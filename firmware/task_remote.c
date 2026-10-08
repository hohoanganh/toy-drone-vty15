/**
 * Bench remote for a toy drone: menu on the OLED, three buttons, packets
 * out of the nRF24L01+. See remote.h.
 *
 *   button 1  next item          button 2  previous item
 *   button 3  act on the item    button 3 held  throttle to 00 (and beep)
 *
 * The radio starts OFF. "LINK" binds (bind packets with both addresses a
 * receiver may be waiting on) and then sends the control packet for good:
 * one packet every 8 ms, two per hop channel, like the original remote.
 *
 * A PC can drive it over the console instead of the buttons: "rc p" sets
 * the whole packet, "rc wd" arms a watchdog that pulls the throttle to 00
 * when the PC stops talking. See cmd_rc.
 */
#if defined(APP_REMOTE)

#include <string.h>

#include "ak.h"
#include "task.h"
#include "timer.h"

#include "hal.h"
#include "xprintf.h"

#include "gfx.h"
#include "kit.h"
#include "remote.h"
#include "task_list.h"

#define TX_PERIOD_MS		(8)
#define BIND_PACKETS		(25)		/* per address: 200 ms each */
#define BTN_DEBOUNCE_MS		(15)
#define HOLD_MS				(700)
#define PULSE_MS			(1000)
#define VISIBLE				(4)
#define PC_DRAW_MS			(150)		/* a PC streaming packets must not redraw on every one */

enum { LINK_OFF, LINK_BIND_A, LINK_BIND_B, LINK_ON };

/* the packet as the original remote sends it with both sticks centred */
static const uint8_t pkt_idle[13] = { 0xDD, 0x80, 0x80, 0x83, 0x80, 0x20, 0x20, 0x20, 0x20, 0x70, 0x04, 0x00, 0x00 };
static uint8_t pkt[13];

static uint8_t link;
static uint8_t radio_ok;
static uint8_t lcd_ok;
static uint16_t tx_n;
static uint32_t sent;
static uint8_t cursor;
static uint8_t dirty;
static uint8_t pulse_byte, pulse_mask;
static uint16_t wd_ms;			/* 0 = no PC watchdog */
static uint32_t pc_ms;			/* when the last "rc p" came */
static uint8_t pc_lost;
static uint32_t draw_ms;
static uint8_t alt_on;
static uint8_t tx_ms = TX_PERIOD_MS;	/* "rc t": the period can be tried out without a rebuild */

/*----------------------------------------------------------------------------
 * menu
 *--------------------------------------------------------------------------*/
enum { K_LINK, K_ADD, K_SET, K_AXIS, K_SPEED, K_BIT, K_PULSE };

typedef struct {
	const char* name;		/* 0 = "Bn.b", made from byte and mask */
	uint8_t kind;
	uint8_t byte;
	uint8_t arg;			/* K_ADD: step (two's complement), K_SET: value, K_BIT/K_PULSE: mask */
} item_t;

static const item_t items[] = {
	{ "LINK",		K_LINK,		0,	0 },
	{ "THR +10",		K_ADD,		3,	0x10 },
	{ "THR -10",		K_ADD,		3,	0xF0 },
	{ "THR MID",	K_SET,		3,	0x83 },
	{ "THR 00",		K_SET,		3,	0x00 },
	{ "ROLL",		K_AXIS,		1,	0 },
	{ "PITCH",		K_AXIS,		2,	0 },
	{ "YAW",		K_AXIS,		4,	0 },
	{ "SPEED",		K_SPEED,	10,	0 },
	{ "LIGHT",		K_BIT,		12,	0x80 },
	{ "FLIP 1s",		K_PULSE,	12,	0x01 },
	{ "HEADLESS",	K_BIT,		10,	0x20 },
	{ "AVOID",	K_BIT,		10,	0x80 },
	{ "RESET",		K_BIT,		11,	0x01 },
	{ "RETURN",		K_BIT,		11,	0x20 },
	{ "MID b7",	K_BIT,		11,	0x80 },
	/* bits seen on air whose meaning is not known yet */
	{ 0,			K_BIT,		11,	0x40 },
	{ 0,			K_BIT,		11,	0x10 },
	{ 0,			K_PULSE,	12,	0x02 },
	{ 0,			K_BIT,		10,	0x04 },
	/* everything else, so that no bit is left untried */
	{ 0,			K_BIT,		10,	0x08 },
	{ 0,			K_BIT,		10,	0x10 },
	{ 0,			K_BIT,		10,	0x40 },
	{ 0,			K_BIT,		11,	0x02 },
	{ 0,			K_BIT,		11,	0x04 },
	{ 0,			K_BIT,		11,	0x08 },
	{ 0,			K_BIT,		12,	0x04 },
	{ 0,			K_BIT,		12,	0x08 },
	{ 0,			K_BIT,		12,	0x10 },
	{ 0,			K_BIT,		12,	0x20 },
	{ 0,			K_BIT,		12,	0x40 },
	{ 0,			K_BIT,		9,	0x01 },
	{ 0,			K_BIT,		9,	0x02 },
	{ 0,			K_BIT,		9,	0x04 },
	{ 0,			K_BIT,		9,	0x08 },
	{ 0,			K_BIT,		9,	0x10 },
	{ 0,			K_BIT,		9,	0x20 },
	{ 0,			K_BIT,		9,	0x40 },
	{ 0,			K_BIT,		9,	0x80 },
	{ "B5 +4",		K_ADD,		5,	0x04 },
	{ "B6 +4",		K_ADD,		6,	0x04 },
	{ "B7 +4",		K_ADD,		7,	0x04 },
	{ "B8 +4",		K_ADD,		8,	0x04 },
	{ "DEFAULTS", K_SET,		0xFF, 0 },
};

#define ITEM_NUM	((uint8_t)(sizeof(items) / sizeof(items[0])))

static char* hex2(char* p, uint8_t v) {
	static const char d[] = "0123456789ABCDEF";

	*p++ = d[v >> 4];
	*p++ = d[v & 15];
	*p = 0;
	return p;
}

static uint8_t bit_no(uint8_t mask) {
	uint8_t n = 0;

	while (mask > 1) {
		mask >>= 1;
		n++;
	}
	return n;
}

static void item_name(const item_t* it, char* buf) {
	if (it->name) {
		strcpy(buf, it->name);
		return;
	}
	*buf++ = 'B';
	if (it->byte >= 10) {
		*buf++ = '1';
	}
	*buf++ = (char)('0' + it->byte % 10);
	*buf++ = '.';
	*buf++ = (char)('0' + bit_no(it->arg));
	*buf = 0;
}

static void item_value(const item_t* it, char* buf) {
	static const char* const st[] = { "OFF", "BIND", "BIND", "ON" };

	switch (it->kind) {
	case K_LINK:
		strcpy(buf, radio_ok || link == LINK_OFF ? st[link] : "NO RF");
		break;
	case K_ADD:
	case K_AXIS:
		hex2(buf, pkt[it->byte]);
		break;
	case K_SET:
		if (it->byte < 13) {
			hex2(buf, pkt[it->byte]);
		}
		else {
			buf[0] = 0;
		}
		break;
	case K_SPEED:
		buf[0] = (char)('1' + (pkt[10] & 3));
		buf[1] = 0;
		break;
	default:
		strcpy(buf, (pkt[it->byte] & it->arg) ? "on" : "off");
		break;
	}
}

static void beep(uint16_t hz, uint16_t ms) {
	kit_buzzer(hz);
	timer_set(TASK_REMOTE_ID, REMOTE_SIG_BEEP_OFF, ms, TIMER_ONE_SHOT);
}

static void link_stop(void) {
	timer_remove_attr(TASK_REMOTE_ID, REMOTE_SIG_TX);
	rf_remote_off();
	link = LINK_OFF;
}

static void link_start(void) {
	radio_ok = rf_remote_setup(0);
	if (radio_ok) {
		link = LINK_BIND_A;
		tx_n = 0;
		sent = 0;
		pc_ms = hal_millis();
		pc_lost = 0;
		timer_set(TASK_REMOTE_ID, REMOTE_SIG_TX, tx_ms, TIMER_ONE_SHOT);
	}
}

static void act(const item_t* it) {
	switch (it->kind) {
	case K_LINK:
		if (link != LINK_OFF) {
			link_stop();
		}
		else {
			link_start();
		}
		break;
	case K_ADD: {
		int16_t v = (int16_t)pkt[it->byte] + (int8_t)it->arg;

		if (it->byte == 3) {				/* throttle saturates, the others wrap inside 6 bits */
			pkt[3] = (uint8_t)(v < 0 ? 0 : v > 255 ? 255 : v);
		}
		else {
			pkt[it->byte] = (uint8_t)(v & 0x3F);
		}
		break;
	}
	case K_SET:
		if (it->byte < 13) {
			pkt[it->byte] = it->arg;
		}
		else {
			memcpy(pkt, pkt_idle, sizeof(pkt));
		}
		break;
	case K_AXIS:							/* centre -> low end -> high end -> centre */
		pkt[it->byte] = pkt[it->byte] == 0x80 ? 0x08 : pkt[it->byte] == 0x08 ? 0xF7 : 0x80;
		break;
	case K_SPEED:
		pkt[10] = (uint8_t)((pkt[10] & ~3) | (((pkt[10] & 3) + 1) % 3));
		break;
	case K_BIT:
		pkt[it->byte] ^= it->arg;
		break;
	case K_PULSE:
		pkt[it->byte] |= it->arg;
		pulse_byte = it->byte;
		pulse_mask = it->arg;
		timer_set(TASK_REMOTE_ID, REMOTE_SIG_PULSE_OFF, PULSE_MS, TIMER_ONE_SHOT);
		break;
	default:
		break;
	}
}

/*----------------------------------------------------------------------------
 * screen: 21 x 8 characters
 *   DRONE  ON          T83
 *   R80 P80 Y80
 *   FL       70 04 00 00  bytes 9..12, the flags
 *   -------------------
 *   four menu lines, the selected one inverted
 *--------------------------------------------------------------------------*/
static void draw(void) {
	static const char* const st[] = { "OFF", "BIND", "BIND", "ON" };
	char buf[24];
	char* p;
	uint8_t top;

	gfx_clear();
	gfx_text(0, 0, "DRONE", 1);
	gfx_text(42, 0, radio_ok || link == LINK_OFF ? st[link] : "NO RF", 1);
	p = buf;
	*p++ = 'T';
	p = hex2(p, pkt[3]);
	gfx_text(GFX_W - 3 * GFX_FONT_W, 0, buf, 1);
	gfx_invert(0, 0, GFX_W, 8);

	p = buf;
	*p++ = 'R'; p = hex2(p, pkt[1]); *p++ = ' ';
	*p++ = 'P'; p = hex2(p, pkt[2]); *p++ = ' ';
	*p++ = 'Y'; p = hex2(p, pkt[4]);
	gfx_text(0, 10, buf, 1);
	p = buf;
	for (uint8_t i = 9; i < 13; i++) {
		p = hex2(p, pkt[i]);
		*p++ = ' ';
	}
	*--p = 0;
	gfx_text(GFX_W - 11 * GFX_FONT_W, 19, buf, 1);
	gfx_text(0, 19, "FL", 1);
	gfx_hline(0, 28, GFX_W, 1);

	top = (uint8_t)(cursor < VISIBLE - 1 ? 0 : cursor - (VISIBLE - 2));
	if (top + VISIBLE > ITEM_NUM) {
		top = (uint8_t)(ITEM_NUM - VISIBLE);
	}
	for (uint8_t r = 0; r < VISIBLE; r++) {
		const item_t* it = &items[top + r];
		int y = 30 + r * 9 - (r == VISIBLE - 1 ? 1 : 0);

		item_name(it, buf);
		gfx_text(3, y, buf, 1);
		item_value(it, buf);
		gfx_text(GFX_W - 2 - gfx_text_width(buf, 1), y, buf, 1);
		if (top + r == cursor) {
			gfx_invert(0, y - 1, GFX_W, 9);
		}
	}
	if (!lcd_ok) {
		/* a display that was not ready at power-up gets another chance
		 * whenever the screen changes */
		lcd_ok = kit_init();
		if (lcd_ok) {
			gfx_flush(1);
		}
	}
	else {
		gfx_flush(0);
	}
	dirty = 0;
	draw_ms = hal_millis();
}

/*----------------------------------------------------------------------------
 * buttons: polled from the main loop, debounced, turned into messages
 *--------------------------------------------------------------------------*/
void task_poll_remote(void) {
	static uint32_t last_ms, b3_down_ms;
	static uint8_t raw, stable, b3_long;
	uint32_t now = hal_millis();
	uint8_t sample, pressed, released;

	if (now - last_ms < BTN_DEBOUNCE_MS) {
		return;
	}
	last_ms = now;
	sample = kit_buttons();
	if (sample != raw) {
		raw = sample;
		return;
	}
	pressed = (uint8_t)(sample & ~stable);
	released = (uint8_t)(stable & ~sample);
	stable = sample;

	if (pressed & KIT_BTN_1) {
		task_post_pure_msg(TASK_REMOTE_ID, REMOTE_SIG_KEY_1);
	}
	if (pressed & KIT_BTN_2) {
		task_post_pure_msg(TASK_REMOTE_ID, REMOTE_SIG_KEY_2);
	}
	if (pressed & KIT_BTN_3) {
		b3_down_ms = now;
		b3_long = 0;
	}
	if ((stable & KIT_BTN_3) && !b3_long && now - b3_down_ms >= HOLD_MS) {
		b3_long = 1;
		task_post_pure_msg(TASK_REMOTE_ID, REMOTE_SIG_HOLD_3);
	}
	if ((released & KIT_BTN_3) && !b3_long) {
		task_post_pure_msg(TASK_REMOTE_ID, REMOTE_SIG_KEY_3);
	}
}

/*----------------------------------------------------------------------------
 * task
 *--------------------------------------------------------------------------*/
void task_remote(ak_msg_t* msg) {
	switch (msg->sig) {
	case REMOTE_SIG_INIT:
		memcpy(pkt, pkt_idle, sizeof(pkt));
		lcd_ok = kit_init();
		radio_ok = rf_remote_setup(0);
		rf_remote_off();
		draw();
		if (lcd_ok) {
			gfx_flush(1);
		}
		xprintf("[RC] remote: display %s, nRF24 %s\n", lcd_ok ? "ok" : "MISSING", radio_ok ? "ok" : "MISSING");
		break;

	case REMOTE_SIG_TX:
		switch (link) {
		case LINK_BIND_A:
		case LINK_BIND_B:
			rf_remote_bind((uint8_t)(link == LINK_BIND_B));
			sent++;
			if (++tx_n >= BIND_PACKETS) {
				tx_n = 0;
				link++;
				rf_remote_setup(1);			/* both what follows use the address of this remote */
				dirty = 1;
			}
			break;
		case LINK_ON:
			if (wd_ms && !pc_lost && (uint32_t)(hal_millis() - pc_ms) > wd_ms) {
				/* the PC went quiet: what the original remote sends with the
				 * throttle stick held down and the other one let go */
				pc_lost = 1;
				pkt[1] = pkt[2] = pkt[4] = 0x80;
				pkt[3] = 0x00;
				beep(900, 250);
				dirty = 1;
			}
			rf_remote_ctrl(pkt, (uint8_t)((tx_n >> 1) % 5));
			tx_n = (uint16_t)((tx_n + 1) % 10);
			sent++;
			break;
		default:
			return;
		}
		timer_set(TASK_REMOTE_ID, REMOTE_SIG_TX, tx_ms, TIMER_ONE_SHOT);
		if (dirty && (uint32_t)(hal_millis() - draw_ms) >= PC_DRAW_MS) {
			draw();
		}
		break;

	case REMOTE_SIG_LINK_ON:
		if (link == LINK_OFF) {
			link_start();
			draw();
		}
		break;

	case REMOTE_SIG_LINK_OFF:
		if (link != LINK_OFF) {
			link_stop();
			draw();
		}
		break;

	case REMOTE_SIG_KEY_1:
		cursor = (uint8_t)((cursor + 1) % ITEM_NUM);
		draw();
		break;

	case REMOTE_SIG_KEY_2:
		cursor = (uint8_t)((cursor + ITEM_NUM - 1) % ITEM_NUM);
		draw();
		break;

	case REMOTE_SIG_KEY_3:
		act(&items[cursor]);
		beep(2000, 25);
		draw();
		break;

	case REMOTE_SIG_HOLD_3:
		pkt[3] = 0x00;						/* what the original remote sends with the stick held down */
		beep(900, 250);
		draw();
		break;

	case REMOTE_SIG_PULSE_OFF:
		pkt[pulse_byte] &= (uint8_t)~pulse_mask;
		draw();
		break;

	case REMOTE_SIG_BEEP_OFF:
		kit_buzzer(0);
		break;

	default:
		break;
	}
}

/*----------------------------------------------------------------------------
 * shell: "rc" state, "rc 1|2|3|h" press a button, "rc go <n>" move to item n,
 * "rc dump" the screen as text (64 lines of 128 characters)
 *
 * for a PC that drives the remote:
 *   rc on | rc off     link on / off (unlike the LINK item, not a toggle)
 *   rc p <13 bytes>    the whole packet in hex; byte 0 is ignored
 *   rc wd <ms>         no "rc p" for that long while linked: throttle 00,
 *                      sticks centred, until the next "rc p". 0 = off
 *   rc t <ms>          period between two packets, 2..20 (8 at power-up)
 *   rc a 0|1           1: byte 0 alternates DD / D5 with the packet id, like the
 *                      original remote. 0 (power-up): always DD
 *--------------------------------------------------------------------------*/
void cmd_rc(const char* args) {
	char name[16], val[8];

	while (*args == ' ') {
		args++;
	}
	if (args[0] >= '1' && args[0] <= '3') {
		task_post_pure_msg(TASK_REMOTE_ID, (uint8_t)(REMOTE_SIG_KEY_1 + (args[0] - '1')));
		return;
	}
	if (args[0] == 'h') {
		task_post_pure_msg(TASK_REMOTE_ID, REMOTE_SIG_HOLD_3);
		return;
	}
	if (args[0] == 'o') {
		task_post_pure_msg(TASK_REMOTE_ID, args[1] == 'n' ? REMOTE_SIG_LINK_ON : REMOTE_SIG_LINK_OFF);
		return;
	}
	if (args[0] == 'p') {
		uint8_t b[13];
		uint8_t n = 0, half = 0, v = 0;

		for (args++; *args; args++) {
			char c = *args;
			uint8_t d;

			if (c == ' ') {
				continue;
			}
			if (c >= '0' && c <= '9') {
				d = (uint8_t)(c - '0');
			}
			else if ((c | 0x20) >= 'a' && (c | 0x20) <= 'f') {
				d = (uint8_t)((c | 0x20) - 'a' + 10);
			}
			else {
				n = 0xFF;
				break;
			}
			v = (uint8_t)((v << 4) | d);
			half ^= 1;
			if (!half) {
				if (n >= sizeof(b)) {
					n = 0xFF;
					break;
				}
				b[n++] = v;
			}
		}
		if (n != sizeof(b) || half) {
			xprintf("rc p: 13 bytes in hex\n");
			return;
		}
		pc_ms = hal_millis();
		pc_lost = 0;
		if (memcmp(pkt + 1, b + 1, sizeof(b) - 1)) {
			memcpy(pkt + 1, b + 1, sizeof(b) - 1);
			dirty = 1;
			if (link == LINK_OFF && (uint32_t)(pc_ms - draw_ms) >= PC_DRAW_MS) {
				draw();
			}
		}
		return;
	}
	if (args[0] == 'a') {
		for (args++; *args == ' '; args++) {
		}
		alt_on = (uint8_t)(*args == '1');
		rf_remote_alt(alt_on);
		return;
	}
	if (args[0] == 't') {
		uint8_t n = 0;

		for (args++; *args == ' '; args++) {
		}
		while (*args >= '0' && *args <= '9') {
			n = (uint8_t)(n * 10 + (*args++ - '0'));
		}
		if (n >= 2 && n <= 20) {
			tx_ms = n;
		}
		return;
	}
	if (args[0] == 'w') {
		uint32_t n = 0;

		for (args += 2; *args == ' '; args++) {
		}
		while (*args >= '0' && *args <= '9') {
			n = n * 10 + (uint32_t)(*args++ - '0');
		}
		wd_ms = (uint16_t)(n > 60000 ? 60000 : n);
		pc_ms = hal_millis();
		pc_lost = 0;
		return;
	}
	if (args[0] == 'g') {
		uint8_t n = 0;

		for (args += 2; *args == ' '; args++) {
		}
		while (*args >= '0' && *args <= '9') {
			n = (uint8_t)(n * 10 + (*args++ - '0'));
		}
		if (n < ITEM_NUM) {
			cursor = n;
			draw();
		}
		return;
	}
	if (args[0] == 'l') {				/* "rc lcd": is anything on the display bus? */
		static const char* const bus[4] = { "SCL PB13 SDA PB12", "SCL PB12 SDA PB13", "SCL PB6 SDA PB7", "SCL PB7 SDA PB6" };

		for (uint8_t b = 0; b < 4; b++) {
			xprintf("%s:", bus[b]);
			for (uint8_t a = 0x08; a < 0x78; a++) {
				if (kit_bus_probe(b, a)) {
					xprintf(" %02X", a);
				}
			}
			xprintf("\n");
		}
		xprintf("buttons now: %02X\n", kit_buttons());
		return;
	}
	if (args[0] == 'd') {
		for (int y = 0; y < GFX_H; y++) {
			for (int x = 0; x < GFX_W; x++) {
				xputc(gfx_get(x, y) ? '#' : '.');
			}
			xputc('\n');
		}
		return;
	}
	item_name(&items[cursor], name);
	item_value(&items[cursor], val);
	xprintf("link %d radio %d lcd %d sent %d item %d/%d \"%s\" = %s wd %d lost %d t %d alt %d\npkt", link, radio_ok, lcd_ok,
			(int)sent, cursor, ITEM_NUM, name, val, wd_ms, pc_lost, tx_ms, alt_on);
	for (uint8_t i = 0; i < 13; i++) {
		xprintf(" %02X", pkt[i]);
	}
	xprintf("\n");
}

#endif /* APP_REMOTE */
