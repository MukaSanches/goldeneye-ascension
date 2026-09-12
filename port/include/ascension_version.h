#ifndef ASCENSION_VERSION_H
#define ASCENSION_VERSION_H

/*
 * Ascension identity/version is intentionally centralized here.
 * Keep runtime surfaces (window title, menu signature, future overlays)
 * derived from these macros so a release bump never drifts between screens.
 */
#define ASCENSION_NAME "Ascension"

#define ASCENSION_VERSION_MAJOR 0
#define ASCENSION_VERSION_MINOR 0
#define ASCENSION_VERSION_PATCH 2
#define ASCENSION_VERSION "0.0.2"

/* Short, restrained signature that fits both the SDL title bar and the
 * low-resolution in-game footer without introducing a new font or asset. */
#define ASCENSION_SIGNATURE ASCENSION_NAME " // " ASCENSION_VERSION
#define ASCENSION_WINDOW_TITLE ASCENSION_SIGNATURE

#endif
