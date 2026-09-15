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

/* V3 directional wheel: positive/negative notches retain their direction in
 * Modern; legacy modes keep the original forward-cycle behavior. */
void inputPostWheel(int notches);
void inputRescanPads(void);

/* V4 live keyboard rebinding used by the F10 Controls page. configKey is one
 * of the existing Input.Bind.* keys, so persistence remains in ge007.ini and
 * no save/ROM format is touched. */
const char *inputBindingDisplay(const char *configKey);
int inputBindingSetScancode(const char *configKey, int scancode);
int inputBindingReset(const char *configKey);

#ifdef __cplusplus
}
#endif

#endif /* PORT_INPUT_H */
