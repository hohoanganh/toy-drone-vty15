/**
 ******************************************************************************
 * @brief:  "rf" shell command: listen with the nRF24L01+ of the AK Base Kit
 *          2.1 (CE PA8, CSN PB9, SPI1 shared with the NOR flash) on one
 *          channel and print what arrives. Built only with -DAPP_RF_TEST.
 *
 *   rf                         registers of the module (is it there?)
 *   rf <ch> <rate> [crc] [a]   ch 0..125; rate 1 = 1 Mbps, 2 = 2 Mbps,
 *                              0 = 250 kbps; crc 0 = raw 32 bytes without
 *                              CRC (default), 1 or 2 = Enhanced ShockBurst
 *                              with dynamic payload and that CRC length;
 *                              a = 1 address reversed, 2 / 3 promiscuous
 *
 *  Raw mode shows the bytes behind the address as they are on air: packet
 *  control field, payload and CRC of the sender, not aligned to bytes.
 ******************************************************************************
**/

#if defined(APP_RF_TEST)

#include "stm32l1xx.h"
#include "stm32l1xx_conf.h"

#include "hal.h"
#include "xprintf.h"

/* Pins of the module as on the kit this was written on (2.1). On the kit 3.0
 * the schematic puts CSN of J6 on PA4: build with -DRF_CSN_PORT=GPIOA
 * -DRF_CSN_PIN=GPIO_Pin_4 there. */
#ifndef RF_CE_PIN
#define RF_CE_PORT			GPIOA
#define RF_CE_PIN			GPIO_Pin_8
#endif
#ifndef RF_CSN_PIN
#define RF_CSN_PORT			GPIOB
#define RF_CSN_PIN			GPIO_Pin_9
#endif

#define RF_LISTEN_MS		(1500U)		/* a handler must return well before the 3 s watchdog of task_system */
#define RF_MAX_PRINT		(30)

/* address the receiver under test writes to RX_ADDR_P0, in the order it writes it */
static uint8_t rf_addr[5] = { 0x4D, 0x41, 0x49, 0x4E, 0xCC };		/* "rf a .." changes it */

static const char* rf_hex(const char* p, uint8_t* v) {
	uint8_t n = 0;

	*v = 0;
	while (*p == ' ') {
		p++;
	}
	for (; n < 2; p++, n++) {
		char c = *p;

		if (c >= '0' && c <= '9') {
			*v = (uint8_t)((*v << 4) | (c - '0'));
		}
		else if (c >= 'a' && c <= 'f') {
			*v = (uint8_t)((*v << 4) | (c - 'a' + 10));
		}
		else if (c >= 'A' && c <= 'F') {
			*v = (uint8_t)((*v << 4) | (c - 'A' + 10));
		}
		else {
			break;
		}
	}
	return n ? p : (const char*)0;
}

static uint8_t rf_xfer(uint8_t b) {
	uint32_t spin = 20000;

	while (!(SPI1->SR & SPI_SR_TXE) && --spin) {
	}
	SPI1->DR = b;
	while (!(SPI1->SR & SPI_SR_RXNE) && --spin) {
	}
	return (uint8_t)SPI1->DR;
}

static inline void rf_csn(uint8_t high) {
	if (high) {
		RF_CSN_PORT->BSRRL = RF_CSN_PIN;
	}
	else {
		RF_CSN_PORT->BSRRH = RF_CSN_PIN;
	}
}

static inline void rf_ce(uint8_t high) {
	if (high) {
		RF_CE_PORT->BSRRL = RF_CE_PIN;
	}
	else {
		RF_CE_PORT->BSRRH = RF_CE_PIN;
	}
}

static uint8_t rf_cmd(uint8_t cmd, const uint8_t* tx, uint8_t* rx, uint8_t len) {
	uint8_t status;

	rf_csn(0);
	status = rf_xfer(cmd);
	for (uint8_t i = 0; i < len; i++) {
		uint8_t v = rf_xfer(tx ? tx[i] : 0xFF);

		if (rx) {
			rx[i] = v;
		}
	}
	rf_csn(1);
	return status;
}

static void rf_wreg(uint8_t reg, uint8_t v) {
	rf_cmd((uint8_t)(0x20 | reg), &v, 0, 1);
}

static uint8_t rf_rreg(uint8_t reg) {
	uint8_t v;

	rf_cmd(reg, 0, &v, 1);
	return v;
}

static void rf_pins(void) {
	GPIO_InitTypeDef gpio;

	RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOA | RCC_AHBPeriph_GPIOB, ENABLE);
	rf_csn(1);
	rf_ce(0);
	GPIO_StructInit(&gpio);
	gpio.GPIO_Mode = GPIO_Mode_OUT;
	gpio.GPIO_OType = GPIO_OType_PP;
	gpio.GPIO_Speed = GPIO_Speed_10MHz;
	gpio.GPIO_PuPd = GPIO_PuPd_NOPULL;
	gpio.GPIO_Pin = RF_CE_PIN;
	GPIO_Init(RF_CE_PORT, &gpio);
	gpio.GPIO_Pin = RF_CSN_PIN;
	GPIO_Init(RF_CSN_PORT, &gpio);
}

static const char* rf_num(const char* p, uint16_t* v) {
	uint8_t n = 0;

	*v = 0;
	while (*p == ' ') {
		p++;
	}
	while (*p >= '0' && *p <= '9' && *v < 1000) {
		*v = (uint16_t)(*v * 10 + (*p++ - '0'));
		n++;
	}
	return n ? p : (const char*)0;
}

/*----------------------------------------------------------------------------
 * transmit side: HS6200 style frames sent with the nRF24L01+ (its own CRC off)
 *   on air after the address: 2 guard bytes (~a0, a0; a0 = address byte
 *   written first), 9 bit PCF (length 6, PID 2, NO_ACK 1), payload XOR
 *   scramble table, CRC16 0x1021 init 0xFFFF over address + PCF + payload
 *   (not the guard bytes), sent MSB first.
 *--------------------------------------------------------------------------*/
static const uint8_t rf_scr[15] = { 0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0 };

/* this transmitter: id and hop channels as sent in the bind packet of the
 * original remote; bind happens on channel 75 with the address "MAIN" + CC */
static const uint8_t rf_bind_addr[5] = { 0x4D, 0x41, 0x49, 0x4E, 0xCC };
static const uint8_t rf_tx_id[4] = { 0xCC, 0x68, 0xC9, 0x21 };
static const uint8_t rf_hop[5] = { 0x48, 0x42, 0x35, 0x3D, 0x31 };
#define RF_BIND_CH			(75)

static uint8_t rf_frame[32];
static uint16_t rf_bitpos;
static uint16_t rf_crc;
static uint8_t rf_pid;

static void rf_put(uint16_t v, uint8_t nbits, uint8_t in_crc) {
	while (nbits--) {
		uint8_t bit = (uint8_t)((v >> nbits) & 1);

		if (bit) {
			rf_frame[rf_bitpos >> 3] |= (uint8_t)(0x80 >> (rf_bitpos & 7));
		}
		rf_bitpos++;
		if (in_crc) {
			uint8_t fb = (uint8_t)(((rf_crc >> 15) & 1) ^ bit);

			rf_crc = (uint16_t)(rf_crc << 1);
			if (fb) {
				rf_crc ^= 0x1021;
			}
		}
	}
}

/* builds rf_frame for one packet, returns its length in bytes */
static uint8_t rf_build(const uint8_t* addr, const uint8_t* msg, uint8_t len) {
	uint16_t crc;

	for (uint8_t i = 0; i < sizeof(rf_frame); i++) {
		rf_frame[i] = 0;
	}
	rf_bitpos = 0;
	rf_crc = 0xFFFF;
	for (int8_t i = 4; i >= 0; i--) {				/* the address is sent by the nRF24 itself: CRC only */
		for (uint8_t b = 0; b < 8; b++) {
			uint8_t fb = (uint8_t)(((rf_crc >> 15) & 1) ^ ((addr[i] >> (7 - b)) & 1));

			rf_crc = (uint16_t)(rf_crc << 1);
			if (fb) {
				rf_crc ^= 0x1021;
			}
		}
	}
	rf_put((uint8_t)~addr[0], 8, 0);
	rf_put(addr[0], 8, 0);
	rf_put(len, 6, 1);
	rf_put(rf_pid & 3, 2, 1);
	rf_put(1, 1, 1);								/* NO_ACK */
	rf_pid++;
	for (uint8_t i = 0; i < len; i++) {
		rf_put((uint8_t)(msg[i] ^ rf_scr[i % 15]), 8, 1);
	}
	crc = rf_crc;
	rf_put(crc, 16, 0);
	return (uint8_t)((rf_bitpos + 7) >> 3);
}

static void rf_tx_setup(const uint8_t* addr) {
	rf_ce(0);
	rf_wreg(0x00, 0x02);							/* PWR_UP, PTX, no CRC of its own */
	rf_wreg(0x01, 0x00);
	rf_wreg(0x02, 0x01);
	rf_wreg(0x03, 0x03);
	rf_wreg(0x04, 0x00);
	rf_wreg(0x06, 0x06);							/* 1 Mbps, 0 dBm */
	rf_wreg(0x1C, 0x00);
	rf_wreg(0x1D, 0x00);
	rf_cmd(0x20 | 0x10, addr, 0, 5);				/* TX_ADDR */
	rf_wreg(0x07, 0x70);
	rf_cmd(0xE1, 0, 0, 0);							/* FLUSH_TX */
	hal_delay_ms(3);
}

static void rf_send(uint8_t ch, uint8_t nbytes) {
	uint32_t spin = 40000;

	rf_wreg(0x05, ch);
	rf_wreg(0x07, 0x70);
	rf_cmd(0xA0, rf_frame, 0, nbytes);				/* W_TX_PAYLOAD */
	rf_ce(1);
	while (!(rf_rreg(0x07) & 0x20) && --spin) {		/* TX_DS */
	}
	rf_ce(0);
}

/* "rf tb [ms]": bind packets; "rf tx <ms> <13 payload bytes>": control packets,
 * two per hop channel 8 ms apart, bit 3 of byte 0 set on odd PIDs like the
 * original remote does. */
static void rf_transmit(const char* p) {
	uint8_t msg[13];
	uint8_t addr[5];
	uint16_t ms = 0;
	uint16_t sent = 0;
	uint8_t bind = (uint8_t)(p[1] == 'b');
	uint8_t n;
	uint32_t t0, tn;
	uint16_t fixed = 0xFFFF;			/* "rf tc <ch> ...": control packets on one channel only */
	const char* q = p + 2;

	if (p[1] == 'c') {
		q = rf_num(q, &fixed);
		if (!q || fixed > 125) {
			xprintf("usage: rf tc <ch> <ms> <13 payload bytes hex>\n");
			return;
		}
	}
	q = rf_num(q, &ms);

	if (!q || ms == 0 || ms > 2000) {
		ms = bind ? 1500 : 1000;					/* a handler must return within 3 s */
	}
	if (bind) {
		msg[0] = 0xB0;
		for (uint8_t i = 0; i < 4; i++) {
			msg[1 + i] = rf_tx_id[i];
		}
		for (uint8_t i = 0; i < 5; i++) {
			msg[5 + i] = rf_hop[i];
		}
		rf_tx_setup(rf_bind_addr);
		t0 = hal_millis();
		while (hal_millis() - t0 < ms) {
			n = rf_build(rf_bind_addr, msg, 10);
			rf_send(RF_BIND_CH, n);
			sent++;
			hal_delay_ms(6);
		}
	}
	else {
		uint8_t i = 0;
		uint8_t len;

		/* "tx": 13 bytes over the hop channels; "tc": 1..13 bytes on one
		 * channel, sent with the address set by "rf a" (experiments) */
		for (; i < 13 && q && (q = rf_hex(q, &msg[i])) != 0; i++) {
		}
		len = i;
		if (len == 0 || (fixed > 125 && len != 13)) {
			xprintf("usage: rf tb [ms] | rf tx <ms> <13 bytes> | rf tc <ch> <ms> <1..13 bytes>\n");
			return;
		}
		for (i = 0; i < 4; i++) {
			addr[i] = rf_tx_id[i];
		}
		addr[4] = 0xCC;
		if (fixed <= 125) {
			for (i = 0; i < 5; i++) {
				addr[i] = rf_addr[i];
			}
		}
		if (p[1] == 'f') {
			/* "rf tf": bind first, without a gap before the control packets.
			 * A receiver fresh from power-up listens on the bind address, one
			 * that lost its remote on the address of that remote: send both. */
			uint8_t bmsg[10];

			bmsg[0] = 0xB0;
			for (i = 0; i < 4; i++) {
				bmsg[1 + i] = rf_tx_id[i];
			}
			for (i = 0; i < 5; i++) {
				bmsg[5 + i] = rf_hop[i];
			}
			for (uint8_t round = 0; round < 2; round++) {
				const uint8_t* a = round ? addr : rf_bind_addr;

				rf_tx_setup(a);
				t0 = hal_millis();
				while (hal_millis() - t0 < 150) {
					n = rf_build(a, bmsg, 10);
					rf_send(RF_BIND_CH, n);
					sent++;
					hal_delay_ms(6);
				}
			}
		}
		rf_tx_setup(addr);
		t0 = hal_millis();
		tn = t0;
		for (uint8_t hop = 0; hal_millis() - t0 < ms; hop = (uint8_t)((hop + 1) % 5)) {
			for (uint8_t k = 0; k < 2; k++) {
				if (len == 13) {
					msg[0] = (uint8_t)((rf_pid & 1) ? (msg[0] | 0x08) : (msg[0] & (uint8_t)~0x08));
				}
				n = rf_build(addr, msg, len);
				rf_send(fixed <= 125 ? (uint8_t)fixed : rf_hop[hop], n);
				sent++;
				tn += 8;
				while ((int32_t)(tn - hal_millis()) > 0) {
				}
			}
		}
	}
	rf_wreg(0x00, 0x00);
	xprintf("%d packet(s) sent, %s\n", sent, bind ? "bind" : "control");
}

void cmd_rf(const char* args) {
	static const char* const rate_name[3] = { "250k", "1M", "2M" };
	static const uint8_t rate_bits[3] = { 0x20, 0x00, 0x08 };
	uint8_t buf[32];
	uint8_t addr[5];
	uint16_t ch, rate, crc = 0, amode = 0;
	uint16_t got = 0;
	uint32_t t0;
	const char* p;

	rf_pins();
	if (!(SPI1->CR1 & SPI_CR1_SPE)) {
		xprintf("SPI1 is off (build without external staging?)\n");
		return;
	}
	p = args;
	while (*p == ' ') {
		p++;
	}
	if (*p == 't' && (p[1] == 'b' || p[1] == 'x' || p[1] == 'c' || p[1] == 'f')) {
		rf_transmit(p);
		return;
	}
	if (*p == 'a') {
		/* "rf a 4D 41 49 4E CC": the address to listen for, in the order
		 * the receiver under test writes it to its RX_ADDR_P0 */
		uint8_t a[5];
		uint8_t i = 0;

		for (p++; i < 5 && (p = rf_hex(p, &a[i])) != 0; i++) {
		}
		if (i == 5) {
			for (i = 0; i < 5; i++) {
				rf_addr[i] = a[i];
			}
		}
		xprintf("address %02X %02X %02X %02X %02X\n", rf_addr[0], rf_addr[1], rf_addr[2], rf_addr[3], rf_addr[4]);
		return;
	}
	if (*p == 's') {
		/* "rf s": carrier scan. RPD (reg 09) is set when more than -64 dBm
		 * was seen on the channel, whatever the modulation or the address:
		 * shows where a transmitter nearby sends, even one the nRF24 cannot
		 * decode. 11 ms per channel = one pass of all 126 in 1.4 s. */
		uint8_t n = 0;

		rf_ce(0);
		rf_wreg(0x01, 0x00);
		rf_wreg(0x02, 0x01);
		rf_wreg(0x06, 0x06);
		rf_wreg(0x00, 0x03);
		hal_delay_ms(5);
		for (ch = 0; ch <= 125; ch++) {
			uint8_t hit = 0;

			rf_wreg(0x05, (uint8_t)ch);
			t0 = hal_millis();
			while (hal_millis() - t0 < 11 && !hit) {
				rf_ce(1);
				for (volatile uint32_t d = 0; d < 1500; d++) {		/* about 300 us: RX settling + RPD */
				}
				hit = rf_rreg(0x09) & 1;
				rf_ce(0);
			}
			if (hit) {
				xprintf("%d ", ch);
				n++;
			}
		}
		rf_wreg(0x00, 0x00);
		xprintf("\n%d channel(s) with a carrier\n", n);
		return;
	}
	p = rf_num(args, &ch);
	if (!p) {
		rf_cmd(0x0A, 0, buf, 5);
		xprintf("CONFIG %02X STATUS %02X RF_CH %02X RF_SETUP %02X SETUP_AW %02X FEATURE %02X\n", rf_rreg(0x00),
				rf_rreg(0x07), rf_rreg(0x05), rf_rreg(0x06), rf_rreg(0x03), rf_rreg(0x1D));
		xprintf("RX_ADDR_P0 %02X %02X %02X %02X %02X\n", buf[0], buf[1], buf[2], buf[3], buf[4]);
		rf_wreg(0x05, 0x2A);
		xprintf("RF_CH write 2A, read back %02X (2A = the module answers)\n", rf_rreg(0x05));
		return;
	}
	p = rf_num(p, &rate);
	if (!p || ch > 125 || rate > 2) {
		xprintf("usage: rf | rf <ch 0..125> <rate 1|2|0=250k> [crc 0=raw|1|2]\n");
		return;
	}
	p = rf_num(p, &crc);
	if (!p || crc > 2) {
		crc = 0;
	}
	/* address mode: 0 as written by the receiver, 1 byte order reversed,
	 * 2 / 3 promiscuous (2 byte "address" 00 AA / 00 55: a preamble, so
	 * anything on the channel comes through, misaligned and with noise) */
	if (!p || !rf_num(p, &amode) || amode > 3) {
		amode = 0;
	}
	for (uint8_t i = 0; i < 5; i++) {
		addr[i] = amode == 1 ? rf_addr[4 - i] : rf_addr[i];
	}
	if (amode >= 2) {
		addr[0] = amode == 2 ? 0xAA : 0x55;
		addr[1] = 0x00;
		crc = 0;
	}

	rf_ce(0);
	rf_wreg(0x00, 0x00);							/* power down while changing */
	rf_wreg(0x01, crc ? 0x01 : 0x00);				/* EN_AA: dynamic payload needs it on the pipe */
	rf_wreg(0x02, 0x01);							/* pipe 0 only */
	rf_wreg(0x03, amode >= 2 ? 0x00 : 0x03);		/* 5 byte address; 00 = the undocumented 2 bytes */
	rf_wreg(0x04, 0x00);							/* no retransmit */
	rf_wreg(0x05, (uint8_t)ch);
	rf_wreg(0x06, (uint8_t)(rate_bits[rate] | 0x06));
	rf_cmd(0x20 | 0x0A, addr, 0, 5);
	rf_wreg(0x11, 32);								/* RX_PW_P0 (ignored with dynamic payload) */
	rf_wreg(0x1D, crc ? 0x04 : 0x00);				/* FEATURE: EN_DPL */
	rf_wreg(0x1C, crc ? 0x01 : 0x00);				/* DYNPD pipe 0 */
	rf_wreg(0x07, 0x70);
	rf_cmd(0xE2, 0, 0, 0);							/* FLUSH_RX */
	rf_wreg(0x00, (uint8_t)(0x03 | (crc ? 0x08 : 0) | (crc == 2 ? 0x04 : 0)));	/* PWR_UP, PRIM_RX, CRC */
	hal_delay_ms(5);
	rf_ce(1);

	xprintf("ch %d (%d MHz) %s %s addr-mode %d, %d ms\n", ch, 2400 + ch, rate_name[rate],
			crc == 0 ? "raw" : crc == 1 ? "ESB crc1" : "ESB crc2", amode, RF_LISTEN_MS);
	t0 = hal_millis();
	while (hal_millis() - t0 < RF_LISTEN_MS) {
		if (rf_rreg(0x07) & 0x40) {
			uint8_t len = 32;

			if (crc) {
				rf_cmd(0x60, 0, &len, 1);			/* R_RX_PL_WID */
				if (len > 32) {
					rf_cmd(0xE2, 0, 0, 0);
					rf_wreg(0x07, 0x70);
					continue;
				}
			}
			rf_cmd(0x61, 0, buf, len);
			rf_wreg(0x07, 0x40);
			if (got < RF_MAX_PRINT) {
				xprintf("%4d ms %2d:", (int)(hal_millis() - t0), len);
				for (uint8_t i = 0; i < len; i++) {
					xprintf(" %02X", buf[i]);
				}
				xprintf("\n");
			}
			got++;
		}
	}
	rf_ce(0);
	rf_wreg(0x00, 0x00);
	xprintf("%d packet(s)\n", got);
}

/*----------------------------------------------------------------------------
 * the same frames for remote/task_remote.c, one packet per call
 *--------------------------------------------------------------------------*/
#if defined(APP_REMOTE)
static void rf_own_addr(uint8_t* addr) {
	for (uint8_t i = 0; i < 4; i++) {
		addr[i] = rf_tx_id[i];
	}
	addr[4] = 0xCC;
}

uint8_t rf_remote_setup(uint8_t mode) {
	uint8_t addr[5];

	rf_pins();
	if (!(SPI1->CR1 & SPI_CR1_SPE)) {
		return 0;
	}
	rf_own_addr(addr);
	rf_tx_setup(mode ? addr : rf_bind_addr);
	rf_wreg(0x05, 0x2A);
	return (uint8_t)(rf_rreg(0x05) == 0x2A);
}

void rf_remote_bind(uint8_t mode) {
	uint8_t addr[5];
	uint8_t msg[10];

	rf_own_addr(addr);
	msg[0] = 0xB0;
	for (uint8_t i = 0; i < 4; i++) {
		msg[1 + i] = rf_tx_id[i];
	}
	for (uint8_t i = 0; i < 5; i++) {
		msg[5 + i] = rf_hop[i];
	}
	rf_send(RF_BIND_CH, rf_build(mode ? addr : rf_bind_addr, msg, 10));
}

static uint8_t rf_alt;

/* 1: bit 3 of byte 0 follows the packet id like on the original remote (measured
 * on air: DD with PID 1 and 3, D5 with PID 0 and 2). 0: the bit is always set. */
void rf_remote_alt(uint8_t on) {
	rf_alt = on;
}

void rf_remote_ctrl(uint8_t* msg, uint8_t hop) {
	uint8_t addr[5];

	rf_own_addr(addr);
	/* The original remote sets bit 3 of byte 0 in every other packet, and
	 * with it the receiver only ever reads the packets that have the bit.
	 * Which packet of a pair the receiver catches from THIS transmitter
	 * depends on timing (its hop order and timing are not the original's,
	 * those have not been measured), so the bit is set in all of them: the
	 * receiver then reads what it reads from the original. What the bit
	 * means is not known. */
	if (rf_alt && !(rf_pid & 1)) {
		msg[0] &= (uint8_t)~0x08;
	}
	else {
		msg[0] |= 0x08;
	}
	rf_send(rf_hop[hop % 5], rf_build(addr, msg, 13));
}

void rf_remote_off(void) {
	rf_ce(0);
	rf_wreg(0x00, 0x00);
}
#endif /* APP_REMOTE */

#endif /* APP_RF_TEST */
