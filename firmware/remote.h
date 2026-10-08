/**
 ******************************************************************************
 * @brief:  Bench remote for a 2.4 GHz toy drone on the AK Base Kit 2.1:
 *          OLED + 3 buttons pick what goes into the 13 byte control packet,
 *          the nRF24L01+ of the kit sends it (HS6200 style frames, see
 *          port/stm32l151/rf_test.c). Built only with -DAPP_REMOTE.
 *
 *  A test tool, not a flight controller: every item of the menu changes one
 *  field or one bit of the packet, so that each can be tried on the drone.
 ******************************************************************************
**/

#ifndef __REMOTE_H__
#define __REMOTE_H__

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdint.h>

#include "ak.h"

enum {
	REMOTE_SIG_INIT = AK_USER_DEFINE_SIG,
	REMOTE_SIG_TX,			/* one-shot timer: send the next packet */
	REMOTE_SIG_KEY_1,		/* next item */
	REMOTE_SIG_KEY_2,		/* previous item */
	REMOTE_SIG_KEY_3,		/* act on the item */
	REMOTE_SIG_HOLD_3,		/* button 3 held: throttle to 0 */
	REMOTE_SIG_PULSE_OFF,	/* one-shot timer: end of a pulsed bit */
	REMOTE_SIG_BEEP_OFF,
	REMOTE_SIG_LINK_ON,		/* from the shell: bind and send (nothing if already on) */
	REMOTE_SIG_LINK_OFF,	/* from the shell: stop sending */
};

extern void task_remote(ak_msg_t* msg);
extern void task_poll_remote(void);
extern void cmd_rc(const char* args);		/* shell: look at / drive the remote */

/* radio side, port/stm32l151/rf_test.c. mode: 0 = bind address ("MAIN"),
 * 1 = address of this remote */
extern uint8_t rf_remote_setup(uint8_t mode);	/* 1 if the nRF24 answers */
extern void rf_remote_bind(uint8_t mode);		/* one bind packet on the bind channel */
extern void rf_remote_ctrl(uint8_t* msg, uint8_t hop);	/* one control packet on hop channel 0..4 */
extern void rf_remote_off(void);
extern void rf_remote_alt(uint8_t on);		/* 1: byte 0 alternates DD / D5 with the packet id */

#ifdef __cplusplus
}
#endif

#endif /* __REMOTE_H__ */
