package com.muka.ascension;

import org.libsdl.app.SDLActivity;

/** SDL host for the Ascension native core. */
public final class GameActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        // The last library is where SDLActivity resolves SDL_main().
        return new String[] { "SDL2", "ascension" };
    }
}
