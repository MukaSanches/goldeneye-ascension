/*
 * Ascension 0.0.3 localization layer.
 *
 * Scope is intentionally narrow: only strings already owned by Ascension's
 * PC overlay are translated. GoldenEye ROM text, mission text and assets are
 * never modified here.
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

/*
 * Keep PT-BR strings ASCII-safe for now. The original Gothic renderer comes
 * from the N64 text path and its UTF-8/extended-glyph behavior is not a stable
 * contract across every ROM region. Correct accents can be enabled later once
 * that coverage is verified rather than risking missing glyphs in 0.0.3.
 */
static const struct LocaleEntry kPtBr[] = {
    /* File-select discovery */
    { "F10 CONTROL", "F10 CONTROLE" },
    { "PRESS F10 TO CONFIGURE", "APERTE F10 PARA CONFIGURAR" },
    { "SELECT FILE", "SELECIONAR ARQUIVO" },

    /* Categories */
    { "DISPLAY", "VIDEO" },
    { "INPUT", "CONTROLES" },
    { "GAMEPLAY", "JOGO" },

    /* Display rows */
    { "Fullscreen", "Tela cheia" },
    { "Windowed or fullscreen display.", "Alterna entre janela e tela cheia." },
    { "Resolution", "Resolucao" },
    { "Window size when not fullscreen.", "Tamanho da janela fora da tela cheia." },
    { "Reduces tearing. Applies now.", "Reduz cortes na imagem. Aplica na hora." },
    { "Frame cap", "Limite de FPS" },
    { "OFF or 30/60/90/120 FPS.", "DESLIGADO ou 30/60/90/120 FPS." },
    { "Display FPS", "Mostrar FPS" },
    { "Show a small FPS counter.", "Mostra um pequeno contador de FPS." },
    { "Smooth edges. Restart required.", "Suaviza serrilhados. Exige reinicio." },
    { "Texture filter", "Filtro de textura" },
    { "Texture sharpness and smoothing.", "Nitidez e suavizacao das texturas." },
    { "Anisotropic", "Anisotropico" },
    { "Sharper distant textures. 1-16.", "Texturas distantes mais nitidas. 1-16." },
    { "FOV scale %", "Escala FOV %" },
    { "View width. Safe range 70-120.", "Largura da visao. Faixa segura 70-120." },
    { "Mipmap compatibility fix", "Correcao de mipmap" },
    { "Keep the port's mipmapped-texture compatibility fix enabled.", "Mantem ativa a correcao de compatibilidade dos mipmaps." },
    { "Texture wrap fix", "Correcao de borda de textura" },
    { "Optional texture-edge compatibility fix. Leave OFF unless needed.", "Correcao opcional nas bordas. Deixe DESLIGADO se nao precisar." },
    { "FPS in window title", "FPS no titulo da janela" },
    { "Show live FPS beside the Ascension window title.", "Mostra o FPS ao vivo no titulo da janela Ascension." },
    { "Quality preset: Performance", "Preset de qualidade: Desempenho" },
    { "Fast preset: 1x MSAA, bilinear, 2x anisotropic.", "Preset rapido: 1x MSAA, bilinear, 2x anisotropico." },
    { "Quality preset: Balanced", "Preset de qualidade: Equilibrado" },
    { "Recommended preset: 2x MSAA, 3-point, 4x anisotropic.", "Preset recomendado: 2x MSAA, 3-pontos, 4x anisotropico." },
    { "Quality preset: Quality", "Preset de qualidade: Qualidade" },
    { "Sharper preset: 4x MSAA, 3-point, 8x anisotropic.", "Preset mais nitido: 4x MSAA, 3-pontos, 8x anisotropico." },
    { "FOV preset", "Preset de FOV" },
    { "Original, Modern or Wide view; Custom keeps manual FOV.", "Visao Original, Moderna ou Ampla; Personalizado mantem o FOV manual." },

    /* Input rows */
    { "Mouse aim speed", "Velocidade ao mirar" },
    { "Aim sensitivity. Range 1-100.", "Sensibilidade da mira. Faixa 1-100." },
    { "Mouse turn speed", "Velocidade ao virar" },
    { "Turn sensitivity. Range 1-100.", "Sensibilidade ao virar. Faixa 1-100." },
    { "Mouse invert Y", "Inverter Y do mouse" },
    { "Reverse vertical mouse look.", "Inverte o eixo vertical do mouse." },
    { "Mouse capture", "Captura do mouse" },
    { "Choose how mouse lock activates.", "Escolhe como o mouse fica preso ao jogo." },
    { "Mouse input", "Entrada do mouse" },
    { "Enable or disable mouse input without changing keyboard/gamepad.", "Ativa ou desativa o mouse sem alterar teclado ou controle." },
    { "Control preset", "Preset de controles" },
    { "Classic, Hybrid or Modern PC controls.", "Controles de PC Classico, Hibrido ou Moderno." },
    { "Dedicated crouch", "Agachar dedicado" },
    { "Enable the Ascension crouch shortcut for Hybrid/Modern.", "Ativa o atalho de agachar do Ascension em Hibrido/Moderno." },
    { "Mouse wheel weapons", "Armas na roda do mouse" },
    { "Use the mouse wheel to cycle weapons.", "Use a roda do mouse para alternar armas." },
    { "Raw mouse input", "Entrada bruta do mouse" },
    { "Bypass OS pointer acceleration for aiming.", "Ignora a aceleracao do ponteiro do sistema ao mirar." },
    { "Mouse smoothing %", "Suavizacao do mouse %" },
    { "Low-pass mouse smoothing. 0 keeps raw motion.", "Suavizacao do movimento do mouse. 0 mantem movimento bruto." },
    { "Mouse Y scale %", "Escala Y do mouse %" },
    { "Vertical mouse sensitivity relative to horizontal.", "Sensibilidade vertical do mouse em relacao a horizontal." },
    { "Aim response band", "Faixa de resposta da mira" },
    { "Fine aim response range above GoldenEye's native gate.", "Faixa de resposta fina da mira acima do limite nativo do GoldenEye." },
    { "Hipfire pitch %", "Mira vertical sem ADS %" },
    { "Vertical look response outside aim mode.", "Resposta vertical fora do modo de mira." },
    { "Menu pointer speed %", "Velocidade do ponteiro %" },
    { "Mouse pointer speed in menus and briefings.", "Velocidade do ponteiro nos menus e briefings." },
    { "Direct menu pointer", "Ponteiro direto nos menus" },
    { "Use the modern 1:1 menu-pointer controller.", "Usa o ponteiro moderno 1:1 nos menus." },
    { "Gamepad deadzone", "Zona morta do controle" },
    { "Left-stick deadzone. Lower is more responsive.", "Zona morta do analogico esquerdo. Menor responde mais rapido." },
    { "Trigger threshold %", "Limite dos gatilhos %" },
    { "Trigger press point for fire/aim.", "Ponto de acionamento dos gatilhos para atirar/mirar." },
    { "Gamepad invert Y", "Inverter Y do controle" },
    { "Reverse vertical look on the right stick.", "Inverte a visao vertical no analogico direito." },
    { "Mouse feel", "Perfil do mouse" },
    { "Classic, Smooth, Modern or Raw PC mouse tuning.", "Ajuste do mouse Classico, Suave, Moderno ou Bruto." },
    { "Gamepad preset", "Preset do controle" },
    { "Classic, Modern, Invert Y or Custom gamepad tuning.", "Ajuste Classico, Moderno, Y Invertido ou Personalizado." },

    /* Gameplay rows */
    { "Language", "Idioma" },
    { "Ascension interface language.", "Idioma da interface do Ascension." },
    { "Screen shake", "Tremor da tela" },
    { "Camera shake. Safe range 0-3.", "Tremor da camera. Faixa segura 0-3." },
    { "Skip intro", "Pular introducao" },
    { "Next launch starts at file select.", "Proximo inicio vai direto aos arquivos." },
    { "Ascension front-end brand", "Marca Ascension na interface" },
    { "Show the Ascension signature and F10 hint on file select.", "Mostra a assinatura Ascension e a dica F10 na selecao de arquivo." },
    { "Reset PC settings", "Redefinir opcoes do PC" },
    { "Restore PC defaults; saves stay safe.", "Restaura padroes do PC; saves ficam seguros." },
    { "Restart game", "Reiniciar jogo" },
    { "Save settings and relaunch.", "Salva opcoes e reinicia o jogo." },
    { "PC settings", "Opcoes do PC" },

    /* Values */
    { "ENGLISH", "INGLES" },
    { "PORTUGUESE (BRAZIL)", "PORTUGUES (BRASIL)" },
    { "OFF", "DESLIGADO" },
    { "ON", "LIGADO" },
    { "NEAREST", "PROXIMO" },
    { "3-POINT", "3-PONTOS" },
    { "ALWAYS GRAB", "SEMPRE PRESO" },
    { "CLICK-TO-LOCK", "CLIQUE P/ TRAVAR" },
    { "CLASSIC", "CLASSICO" },
    { "HYBRID", "HIBRIDO" },
    { "MODERN", "MODERNO" },
    { "ORIGINAL", "ORIGINAL" },
    { "WIDE", "AMPLO" },
    { "CUSTOM", "PERSONALIZADO" },
    { "SMOOTH", "SUAVE" },
    { "RAW", "BRUTO" },
    { "INVERT Y", "Y INVERTIDO" },
    { "PERFORMANCE", "DESEMPENHO" },
    { "BALANCED", "EQUILIBRADO" },
    { "QUALITY", "QUALIDADE" },
    { "CONFIRM", "CONFIRMAR" },
    { "RESET", "REDEFINIR" },
    { "RESTART", "REINICIAR" },
    { "APPLY", "APLICAR" },
    { "FULLSCREEN", "TELA CHEIA" },

    /* Feedback */
    { "RESTART REQUIRED", "EXIGE REINICIO" },
    { "APPLIED", "APLICADO" },
    { "PRESET UNAVAILABLE", "PRESET INDISPONIVEL" },
    { "DEFAULTS RESTORED", "PADROES RESTAURADOS" },
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
