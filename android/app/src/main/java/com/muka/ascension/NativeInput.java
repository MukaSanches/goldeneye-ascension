package com.muka.ascension;

/** Thin JNI surface owned by android/src/mobile_input.c. */
public final class NativeInput {
    public static final int BTN_FIRE = 1 << 0;
    public static final int BTN_AIM = 1 << 1;
    public static final int BTN_USE = 1 << 2;
    public static final int BTN_RELOAD = 1 << 3;
    public static final int BTN_CROUCH = 1 << 4;
    public static final int BTN_NEXT_WEAPON = 1 << 5;
    public static final int BTN_PREV_WEAPON = 1 << 6;
    public static final int BTN_PAUSE = 1 << 7;
    public static final int BTN_WATCH = 1 << 8;

    private NativeInput() {}

    public static native void setMove(float x, float y);
    public static native void setLook(float x, float y);
    public static native void addGyro(float x, float y);
    public static native void setButton(int button, boolean down);
    public static native void setTouchActive(boolean active);
    public static native void reset();
}
