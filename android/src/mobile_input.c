#include <jni.h>
#include <pthread.h>
#include <string.h>

#include "mobile_input.h"

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static MobileInputSnapshot g_state;

static float clampAxis(float v)
{
    if (v < -1.0f) return -1.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

static float accumulateMotion(float current, float delta)
{
    if (delta < -64.0f) delta = -64.0f;
    if (delta > 64.0f) delta = 64.0f;
    current += delta;
    if (current < -256.0f) current = -256.0f;
    if (current > 256.0f) current = 256.0f;
    return current;
}

void mobileInputSetMove(float x, float y)
{
    pthread_mutex_lock(&g_lock);
    g_state.move_x = clampAxis(x);
    g_state.move_y = clampAxis(y);
    pthread_mutex_unlock(&g_lock);
}

void mobileInputSetLook(float x, float y)
{
    pthread_mutex_lock(&g_lock);
    g_state.look_x = accumulateMotion(g_state.look_x, x);
    g_state.look_y = accumulateMotion(g_state.look_y, y);
    pthread_mutex_unlock(&g_lock);
}

void mobileInputAddGyro(float x, float y)
{
    pthread_mutex_lock(&g_lock);
    g_state.gyro_x = accumulateMotion(g_state.gyro_x, x);
    g_state.gyro_y = accumulateMotion(g_state.gyro_y, y);
    pthread_mutex_unlock(&g_lock);
}

void mobileInputSetButton(uint32_t button, int down)
{
    pthread_mutex_lock(&g_lock);
    if (down) g_state.buttons |= button;
    else g_state.buttons &= ~button;
    pthread_mutex_unlock(&g_lock);
}

void mobileInputSetTouchActive(int active)
{
    pthread_mutex_lock(&g_lock);
    g_state.touch_active = active != 0;
    if (!g_state.touch_active) {
        g_state.move_x = g_state.move_y = 0.0f;
        g_state.look_x = g_state.look_y = 0.0f;
        g_state.gyro_x = g_state.gyro_y = 0.0f;
        g_state.buttons = 0;
    }
    pthread_mutex_unlock(&g_lock);
}

void mobileInputSnapshot(MobileInputSnapshot *out, int consumeMotion)
{
    if (!out) return;
    pthread_mutex_lock(&g_lock);
    *out = g_state;
    if (consumeMotion) {
        g_state.look_x = g_state.look_y = 0.0f;
        g_state.gyro_x = g_state.gyro_y = 0.0f;
    }
    pthread_mutex_unlock(&g_lock);
}

void mobileInputReset(void)
{
    pthread_mutex_lock(&g_lock);
    memset(&g_state, 0, sizeof(g_state));
    pthread_mutex_unlock(&g_lock);
}

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_setMove(JNIEnv *env, jclass cls, jfloat x, jfloat y)
{ (void)env; (void)cls; mobileInputSetMove(x, y); }

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_setLook(JNIEnv *env, jclass cls, jfloat x, jfloat y)
{ (void)env; (void)cls; mobileInputSetLook(x, y); }

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_addGyro(JNIEnv *env, jclass cls, jfloat x, jfloat y)
{ (void)env; (void)cls; mobileInputAddGyro(x, y); }

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_setButton(JNIEnv *env, jclass cls, jint button, jboolean down)
{ (void)env; (void)cls; mobileInputSetButton((uint32_t)button, down ? 1 : 0); }

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_setTouchActive(JNIEnv *env, jclass cls, jboolean active)
{ (void)env; (void)cls; mobileInputSetTouchActive(active ? 1 : 0); }

JNIEXPORT void JNICALL
Java_com_muka_ascension_NativeInput_reset(JNIEnv *env, jclass cls)
{ (void)env; (void)cls; mobileInputReset(); }
