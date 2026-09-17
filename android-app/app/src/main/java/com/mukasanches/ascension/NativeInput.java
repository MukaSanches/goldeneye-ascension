package com.mukasanches.ascension;

final class NativeInput {
    static final int FIRE        = 1 << 0;
    static final int AIM         = 1 << 1;
    static final int USE         = 1 << 2;
    static final int RELOAD      = 1 << 3;
    static final int CROUCH      = 1 << 4;
    static final int NEXT_WEAPON = 1 << 5;
    static final int PREV_WEAPON = 1 << 6;
    static final int PAUSE       = 1 << 7;
    static final int WATCH       = 1 << 8;

    private NativeInput() {}

    static native void setMove(float x, float y);
    static native void setLook(float x, float y);
    static native void addGyro(float x, float y);
    static native void setButton(int button, boolean down);
    static native void setTouchActive(boolean active);
    static native void reset();
}
