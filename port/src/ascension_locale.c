/*
 * Ascension localization layer.
 *
 * English remains the original interface language. PT-BR strings are UTF-8;
 * the PC text bridge renders Brazilian Portuguese accents without modifying
 * the original ROM font assets.
 */

#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "system.h"
#include "config.h"
#include "optionsoverlay.h"
#include "ascension_locale.h"

struct LocaleEntry {
    const char *en;
    const char *pt;
};

static int s_language;
static int s_eventWatchInstalled;

static const struct LocaleEntry kPtBr[] = {
    /* File-select discovery */
    { "F10 CONTROL", "F10 CONTROLE" },
    { "PRESS F10 TO CONFIGURE", "APERTE F10 PARA CONFIGURAR" },
    { "SELECT FILE", "SELECIONAR ARQUIVO" },

    /* Categories */
    { "DISPLAY", "VÍDEO" },
    { "INPUT", "CONTROLES" },
    { "GAMEPLAY", "JOGO" },

    /* Display rows */
    { "Fullscreen", "Tela cheia" },
    { "Windowed or fullscreen display.", "Alterna entre janela e tela cheia." },
    { "Resolution", "Resolução" },
    { "Window size when not fullscreen.", "Tamanho da janela fora da tela cheia." },
    { "Reduces tearing. Applies now.", "Reduz cortes na imagem. Aplica na hora." },
    { "Frame cap", "Limite de FPS" },
    { "OFF or 30/60/90/120 FPS.", "DESLIGADO ou 30/60/90/120 FPS." },
    { "Display FPS", "Mostrar FPS" },
    { "Show a small FPS counter.", "Mostra um pequeno contador de FPS." },
    { "Smooth edges. Restart required.", "Suaviza serrilhados. Exige reinício." },
    { "Texture filter", "Filtro de textura" },
    { "Texture sharpness and smoothing.", "Nitidez e suavização das texturas." },
    { "Anisotropic", "Anisotrópico" },
    { "Sharper distant textures. 1-16.", "Texturas distantes mais nítidas. 1-16." },
    { "FOV scale %", "Escala FOV %" },
    { "View width. Safe range 70-120.", "Largura da visão. Faixa segura 70-120." },

    /* Input rows */
    { "Mouse aim speed", "Velocidade ao mirar" },
    { "Aim sensitivity. Range 1-100.", "Sensibilidade da mira. Faixa 1-100." },
    { "Mouse turn speed", "Velocidade ao virar" },
    { "Turn sensitivity. Range 1-100.", "Sensibilidade ao virar. Faixa 1-100." },
    { "Mouse invert Y", "Inverter Y do mouse" },
    { "Reverse vertical mouse look.", "Inverte o eixo vertical do mouse." },
    { "Mouse capture", "Captura do mouse" },
    { "Choose how mouse lock activates.", "Escolhe como o mouse fica preso ao jogo." },

    /* Gameplay rows */
    { "Language", "Idioma" },
    { "Interface and in-game text language.", "Idioma da interface e dos textos do jogo." },
    { "Screen shake", "Tremor da tela" },
    { "Camera shake. Safe range 0-3.", "Tremor da câmera. Faixa segura 0-3." },
    { "Skip intro", "Pular introdução" },
    { "Next launch starts at file select.", "Próximo início vai direto aos arquivos." },
    { "Reset PC settings", "Redefinir opções do PC" },
    { "Restore PC defaults; saves stay safe.", "Restaura padrões do PC; saves ficam seguros." },
    { "Restart game", "Reiniciar jogo" },
    { "Save settings and relaunch.", "Salva opções e reinicia o jogo." },
    { "PC settings", "Opções do PC" },

    /* Values */
    { "ENGLISH", "INGLÊS" },
    { "PORTUGUESE (BRAZIL)", "PORTUGUÊS (BRASIL)" },
    { "OFF", "DESLIGADO" },
    { "ON", "LIGADO" },
    { "NEAREST", "MAIS PRÓXIMO" },
    { "3-POINT", "3-PONTOS" },
    { "ALWAYS GRAB", "SEMPRE PRESO" },
    { "CLICK-TO-LOCK", "CLIQUE P/ TRAVAR" },
    { "CONFIRM", "CONFIRMAR" },
    { "RESET", "REDEFINIR" },
    { "RESTART", "REINICIAR" },
    { "FULLSCREEN", "TELA CHEIA" },

    /* Feedback */
    { "RESTART REQUIRED", "EXIGE REINÍCIO" },
    { "APPLIED", "APLICADO" },
    { "DEFAULTS RESTORED", "PADRÕES RESTAURADOS" },
    { "PRESS AGAIN TO RESET", "REPITA P/ REDEFINIR" },
    { "PRESS AGAIN TO RESTART", "REPITA P/ REINICIAR" },
    { "RESTARTING", "REINICIANDO" },
    { "RESTART FAILED", "FALHA AO REINICIAR" },
    { "WINDOWED MODE ONLY", "APENAS EM JANELA" },
};

#define NUM_PTBR ((int)(sizeof(kPtBr) / sizeof(kPtBr[0])))

PD_CONSTRUCTOR static void localeConfigInit(void)
{
    /* 0 = English, 1 = Portuguese (Brazil). */
    configRegisterInt("Ascension.Language", &s_language, 0, 1);
}

static int SDLCALL localeEventWatch(void *userdata, SDL_Event *event)
{
    (void)userdata;

    if (event->type != SDL_KEYDOWN || event->key.repeat)
        return 1;

    if (event->key.keysym.sym != SDLK_F9 || !optionsOverlayIsOpen())
        return 1;

    s_language = s_language ? 0 : 1;
    configSave();

    sysLogPrintf(LOG_INFO, "ascension: interface language -> %s",
                 s_language ? "pt-BR" : "en");
    return 1;
}

static void ensureEventWatch(void)
{
    if (s_eventWatchInstalled)
        return;

    SDL_AddEventWatch(localeEventWatch, NULL);
    s_eventWatchInstalled = 1;
}

int ascensionLocaleGet(void)
{
    return s_language ? 1 : 0;
}

const char *ascensionLocaleText(const char *text)
{
    if (!text)
        return "";

    ensureEventWatch();

    /* Keep language switching visible even while English is selected. */
    if (!s_language) {
        if (strcmp(text, "TAB CATEGORY  F10 CLOSE") == 0)
            return "TAB CATEGORY  F9 PT-BR  F10 CLOSE";
        if (strcmp(text, "TAB CATEGORY") == 0)
            return "TAB CATEGORY  F9 PT-BR";
        return text;
    }

    if (strcmp(text, "TAB CATEGORY  F10 CLOSE") == 0)
        return "TAB CATEGORIA  F9 EN  F10 FECHAR";
    if (strcmp(text, "TAB CATEGORY") == 0)
        return "TAB CATEGORIA  F9 EN";

    for (int i = 0; i < NUM_PTBR; i++) {
        if (strcmp(text, kPtBr[i].en) == 0)
            return kPtBr[i].pt;
    }

    return text;
}
