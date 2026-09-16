#ifndef PORT_INPUT_H
#define PORT_INPUT_H

#include <PR/ultratypes.h>

#ifdef __cplusplus
extern "C" {
#endif

int  inputInit(void);
void inputDestroy(void);
void inputUpdate(void);
int  inputGetNumControllers(void);
int  inputConnectedMask(void);
unsigned inputComputePad(int idx, signed char *stick_x, signed char *stick_y);

void inputSetMouseGrab(int on);
void inputNotifyClick(void);
int  inputReleaseCapture(void);
int  inputMouseCaptureActive(void);
void inputSuspendForOverlay(void);
void inputPostWheel(int notches);
void inputRescanPads(void);

/* Live F10 keyboard remapping. */
const char *inputBindingDisplay(const char *configKey);
int inputBindingSetScancode(const char *configKey, int scancode);
int inputBindingReset(const char *configKey);

/* Live F10 Modern gamepad remapping. Capture returns 1 after saving a button,
 * 0 while no button is down, and -1 when controller 0 is unavailable. */
const char *inputPadBindingDisplay(const char *configKey);
int inputPadBindingCapturePressed(const char *configKey);
int inputPadBindingReset(const char *configKey);

#ifdef __cplusplus
}
#endif

#endif /* PORT_INPUT_H */
