package com.muka.ascension;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PointF;
import android.util.SparseIntArray;
import android.view.MotionEvent;
import android.view.View;

import java.util.ArrayList;
import java.util.List;

/**
 * Transparent multi-touch FPS control layer rendered above SDL.
 *
 * The left thumb is a floating movement stick. The right thumb is a floating
 * look stick. Buttons are hit-tested before either stick so multiple fingers
 * can move, aim and fire simultaneously.
 */
public final class MobileControlsView extends View {
    private static final int NO_POINTER = -1;

    private static final class TouchButton {
        final float x;
        final float y;
        final float radius;
        final String label;
        final int bit;

        TouchButton(float x, float y, float radius, String label, int bit) {
            this.x = x;
            this.y = y;
            this.radius = radius;
            this.label = label;
            this.bit = bit;
        }
    }

    private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint strokePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final SparseIntArray pointerButtons = new SparseIntArray();
    private final List<TouchButton> buttons = new ArrayList<>();

    private int leftPointer = NO_POINTER;
    private int rightPointer = NO_POINTER;

    private final PointF leftOrigin = new PointF();
    private final PointF leftKnob = new PointF();
    private final PointF rightOrigin = new PointF();
    private final PointF rightKnob = new PointF();

    private float stickRadius;
    private float knobRadius;

    public MobileControlsView(Context context) {
        super(context);
        setFocusable(false);
        setClickable(true);
        setBackgroundColor(Color.TRANSPARENT);

        fillPaint.setStyle(Paint.Style.FILL);
        strokePaint.setStyle(Paint.Style.STROKE);
        strokePaint.setStrokeWidth(dp(2));
        textPaint.setTextAlign(Paint.Align.CENTER);
        textPaint.setFakeBoldText(true);
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        float shortSide = Math.min(w, h);
        stickRadius = clamp(shortSide * 0.135f, dp(64), dp(118));
        knobRadius = stickRadius * 0.43f;

        buttons.clear();
        float big = clamp(shortSide * 0.082f, dp(40), dp(72));
        float medium = big * 0.78f;
        float small = big * 0.64f;

        // Keep the center-right region free for the floating look stick.
        buttons.add(new TouchButton(0.905f, 0.685f, big, "TIRO", NativeInput.BTN_FIRE));
        buttons.add(new TouchButton(0.785f, 0.805f, medium, "MIRA", NativeInput.BTN_AIM));
        buttons.add(new TouchButton(0.865f, 0.485f, medium, "USAR", NativeInput.BTN_USE));
        buttons.add(new TouchButton(0.735f, 0.565f, small, "REC.", NativeInput.BTN_RELOAD));
        buttons.add(new TouchButton(0.650f, 0.825f, small, "AGACH.", NativeInput.BTN_CROUCH));
        buttons.add(new TouchButton(0.940f, 0.315f, small, "ARMA", NativeInput.BTN_NEXT_WEAPON));
        buttons.add(new TouchButton(0.815f, 0.205f, small * 0.92f, "RELÓGIO", NativeInput.BTN_WATCH));
        buttons.add(new TouchButton(0.945f, 0.115f, small * 0.88f, "PAUSA", NativeInput.BTN_PAUSE));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        drawIdleStick(canvas, getWidth() * 0.175f, getHeight() * 0.735f, "MOV.");
        drawIdleStick(canvas, getWidth() * 0.555f, getHeight() * 0.735f, "OLHAR");

        if (leftPointer != NO_POINTER) {
            drawActiveStick(canvas, leftOrigin, leftKnob);
        }
        if (rightPointer != NO_POINTER) {
            drawActiveStick(canvas, rightOrigin, rightKnob);
        }

        for (TouchButton button : buttons) {
            float cx = button.x * getWidth();
            float cy = button.y * getHeight();
            boolean pressed = isButtonPressed(button.bit);

            fillPaint.setColor(pressed
                    ? Color.argb(150, 238, 205, 92)
                    : Color.argb(72, 20, 20, 24));
            strokePaint.setColor(pressed
                    ? Color.argb(235, 255, 228, 130)
                    : Color.argb(145, 238, 205, 92));
            canvas.drawCircle(cx, cy, button.radius, fillPaint);
            canvas.drawCircle(cx, cy, button.radius, strokePaint);

            textPaint.setColor(pressed ? Color.rgb(18, 18, 20) : Color.argb(220, 245, 235, 196));
            textPaint.setTextSize(Math.max(dp(9), button.radius * 0.34f));
            Paint.FontMetrics fm = textPaint.getFontMetrics();
            canvas.drawText(button.label, cx, cy - (fm.ascent + fm.descent) * 0.5f, textPaint);
        }
    }

    private void drawIdleStick(Canvas canvas, float cx, float cy, String label) {
        fillPaint.setColor(Color.argb(26, 255, 255, 255));
        strokePaint.setColor(Color.argb(70, 255, 255, 255));
        canvas.drawCircle(cx, cy, stickRadius, fillPaint);
        canvas.drawCircle(cx, cy, stickRadius, strokePaint);

        textPaint.setColor(Color.argb(80, 255, 255, 255));
        textPaint.setTextSize(dp(10));
        Paint.FontMetrics fm = textPaint.getFontMetrics();
        canvas.drawText(label, cx, cy - (fm.ascent + fm.descent) * 0.5f, textPaint);
    }

    private void drawActiveStick(Canvas canvas, PointF origin, PointF knob) {
        fillPaint.setColor(Color.argb(44, 238, 205, 92));
        strokePaint.setColor(Color.argb(170, 238, 205, 92));
        canvas.drawCircle(origin.x, origin.y, stickRadius, fillPaint);
        canvas.drawCircle(origin.x, origin.y, stickRadius, strokePaint);

        fillPaint.setColor(Color.argb(145, 238, 205, 92));
        canvas.drawCircle(knob.x, knob.y, knobRadius, fillPaint);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        int action = event.getActionMasked();
        int index = event.getActionIndex();

        switch (action) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_POINTER_DOWN:
                assignPointer(event.getPointerId(index), event.getX(index), event.getY(index));
                break;

            case MotionEvent.ACTION_MOVE:
                for (int i = 0; i < event.getPointerCount(); i++) {
                    updatePointer(event.getPointerId(i), event.getX(i), event.getY(i));
                }
                break;

            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_POINTER_UP:
                releasePointer(event.getPointerId(index));
                break;

            case MotionEvent.ACTION_CANCEL:
                resetAll();
                break;

            default:
                break;
        }

        invalidate();
        return true;
    }

    private void assignPointer(int id, float x, float y) {
        int button = hitButton(x, y);
        if (button != 0) {
            pointerButtons.put(id, button);
            NativeInput.setButton(button, true);
            return;
        }

        if (x < getWidth() * 0.43f && leftPointer == NO_POINTER) {
            leftPointer = id;
            leftOrigin.set(x, y);
            leftKnob.set(x, y);
            updateLeft(x, y);
            return;
        }

        if (rightPointer == NO_POINTER) {
            rightPointer = id;
            rightOrigin.set(x, y);
            rightKnob.set(x, y);
            updateRight(x, y);
        }
    }

    private void updatePointer(int id, float x, float y) {
        if (id == leftPointer) {
            updateLeft(x, y);
        } else if (id == rightPointer) {
            updateRight(x, y);
        }
    }

    private void updateLeft(float x, float y) {
        setClampedKnob(leftOrigin, leftKnob, x, y);
        NativeInput.setMove(
                (leftKnob.x - leftOrigin.x) / stickRadius,
                (leftKnob.y - leftOrigin.y) / stickRadius);
    }

    private void updateRight(float x, float y) {
        setClampedKnob(rightOrigin, rightKnob, x, y);
        NativeInput.setLook(
                (rightKnob.x - rightOrigin.x) / stickRadius,
                (rightKnob.y - rightOrigin.y) / stickRadius);
    }

    private void setClampedKnob(PointF origin, PointF knob, float x, float y) {
        float dx = x - origin.x;
        float dy = y - origin.y;
        float len = (float) Math.hypot(dx, dy);
        if (len > stickRadius && len > 0.0f) {
            float scale = stickRadius / len;
            dx *= scale;
            dy *= scale;
        }
        knob.set(origin.x + dx, origin.y + dy);
    }

    public boolean hasActiveTouch() {
        return leftPointer != NO_POINTER
                || rightPointer != NO_POINTER
                || pointerButtons.size() > 0;
    }

    private void releasePointer(int id) {
        if (id == leftPointer) {
            leftPointer = NO_POINTER;
            NativeInput.setMove(0.0f, 0.0f);
        }
        if (id == rightPointer) {
            rightPointer = NO_POINTER;
            NativeInput.setLook(0.0f, 0.0f);
        }

        int bit = pointerButtons.get(id, 0);
        if (bit != 0) {
            pointerButtons.delete(id);
            if (!isButtonPressed(bit)) {
                NativeInput.setButton(bit, false);
            }
        }
    }

    private void resetAll() {
        for (int i = 0; i < pointerButtons.size(); i++) {
            NativeInput.setButton(pointerButtons.valueAt(i), false);
        }
        pointerButtons.clear();
        leftPointer = NO_POINTER;
        rightPointer = NO_POINTER;
        NativeInput.setMove(0.0f, 0.0f);
        NativeInput.setLook(0.0f, 0.0f);
    }

    private int hitButton(float x, float y) {
        for (TouchButton button : buttons) {
            float dx = x - button.x * getWidth();
            float dy = y - button.y * getHeight();
            if (dx * dx + dy * dy <= button.radius * button.radius) {
                return button.bit;
            }
        }
        return 0;
    }

    private boolean isButtonPressed(int bit) {
        for (int i = 0; i < pointerButtons.size(); i++) {
            if (pointerButtons.valueAt(i) == bit) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected void onDetachedFromWindow() {
        resetAll();
        super.onDetachedFromWindow();
    }

    private float dp(float value) {
        return value * getResources().getDisplayMetrics().density;
    }

    private static float clamp(float value, float lo, float hi) {
        return value < lo ? lo : (value > hi ? hi : value);
    }
}
