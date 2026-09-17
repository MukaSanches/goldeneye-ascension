package com.muka.ascension;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;

/**
 * First-run host. The APK contains no copyrighted ROM data: the user selects
 * a legally obtained NTSC-U GoldenEye ROM, which is copied into app-private
 * storage using the exact filename consumed by romdataInit().
 */
public final class LauncherActivity extends Activity {
    private static final int PICK_ROM = 1001;
    private static final String ROM_DIR = "data";
    private static final String ROM_NAME = "ge007.ntsc-final.z64";
    private static final long MIN_REASONABLE_ROM_BYTES = 8L * 1024L * 1024L;
    private static final long MAX_REASONABLE_ROM_BYTES = 64L * 1024L * 1024L;

    private LinearLayout root;
    private Button pickButton;
    private ProgressBar progress;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        File stored = getStoredRom();
        if (isValidGoldenEyeRom(stored)) {
            launchGame();
            return;
        }
        if (stored.exists()) {
            //noinspection ResultOfMethodCallIgnored
            stored.delete();
        }
        showImporter();
    }

    private void showImporter() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setPadding(dp(28), dp(28), dp(28), dp(28));
        root.setBackgroundColor(Color.rgb(10, 10, 12));

        TextView title = new TextView(this);
        title.setText("GoldenEye Ascension");
        title.setTextColor(Color.rgb(238, 205, 92));
        title.setTextSize(28f);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView body = new TextView(this);
        body.setText("Para iniciar, selecione sua própria ROM legal de GoldenEye 007 NTSC-U no formato .z64. A ROM será copiada apenas para o armazenamento privado do aplicativo e não faz parte do APK.");
        body.setTextColor(Color.LTGRAY);
        body.setTextSize(16f);
        body.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams bodyParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        bodyParams.setMargins(0, dp(22), 0, dp(22));
        root.addView(body, bodyParams);

        pickButton = new Button(this);
        pickButton.setText("Selecionar ROM");
        pickButton.setOnClickListener(v -> openPicker());
        root.addView(pickButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        progress = new ProgressBar(this);
        progress.setIndeterminate(true);
        progress.setVisibility(View.GONE);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(dp(48), dp(48));
        progressParams.setMargins(0, dp(18), 0, 0);
        root.addView(progress, progressParams);

        status = new TextView(this);
        status.setTextColor(Color.LTGRAY);
        status.setTextSize(14f);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        statusParams.setMargins(0, dp(12), 0, 0);
        root.addView(status, statusParams);

        setContentView(root);
    }

    private void openPicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        startActivityForResult(intent, PICK_ROM);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_ROM || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }

        Uri uri = data.getData();
        pickButton.setEnabled(false);
        progress.setVisibility(View.VISIBLE);
        status.setText("Importando e validando ROM…");
        new Thread(() -> importRom(uri), "AscensionRomImport").start();
    }

    private void importRom(Uri uri) {
        File dataDir = new File(getFilesDir(), ROM_DIR);
        File target = getStoredRom();
        File temp = new File(dataDir, ROM_NAME + ".tmp");

        try {
            if (!dataDir.exists() && !dataDir.mkdirs()) {
                throw new IOException("Não foi possível criar o diretório privado do jogo.");
            }
            //noinspection ResultOfMethodCallIgnored
            temp.delete();

            long total = 0;
            byte[] buffer = new byte[128 * 1024];
            try (InputStream in = getContentResolver().openInputStream(uri);
                 FileOutputStream out = new FileOutputStream(temp)) {
                if (in == null) {
                    throw new IOException("O Android não conseguiu abrir o arquivo selecionado.");
                }
                int read;
                while ((read = in.read(buffer)) != -1) {
                    total += read;
                    if (total > MAX_REASONABLE_ROM_BYTES) {
                        throw new IOException("O arquivo é grande demais para ser uma ROM válida de GoldenEye.");
                    }
                    out.write(buffer, 0, read);
                }
                out.getFD().sync();
            }

            if (total < MIN_REASONABLE_ROM_BYTES || !isValidGoldenEyeRom(temp)) {
                throw new IOException("A ROM não corresponde ao GoldenEye 007 NTSC-U esperado pelo Ascension.");
            }

            //noinspection ResultOfMethodCallIgnored
            target.delete();
            if (!temp.renameTo(target)) {
                throw new IOException("Falha ao finalizar a importação da ROM.");
            }

            runOnUiThread(this::launchGame);
        } catch (Exception e) {
            //noinspection ResultOfMethodCallIgnored
            temp.delete();
            runOnUiThread(() -> showImportError(e.getMessage()));
        }
    }

    private boolean isValidGoldenEyeRom(File file) {
        if (!file.isFile() || file.length() < 0x40) {
            return false;
        }

        byte[] header = new byte[0x40];
        try (FileInputStream in = new FileInputStream(file)) {
            int off = 0;
            while (off < header.length) {
                int read = in.read(header, off, header.length - off);
                if (read < 0) return false;
                off += read;
            }
        } catch (IOException e) {
            return false;
        }

        byte[] magic = new byte[] { (byte) 0x80, 0x37, 0x12, 0x40 };
        byte[] name = new byte[] { (byte) 'G', (byte) 'O', (byte) 'L', (byte) 'D', (byte) 'E', (byte) 'N', (byte) 'E', (byte) 'Y', (byte) 'E' };
        return Arrays.equals(Arrays.copyOfRange(header, 0, 4), magic)
                && Arrays.equals(Arrays.copyOfRange(header, 0x20, 0x29), name)
                && header[0x3C] == (byte) 'G'
                && header[0x3D] == (byte) 'E'
                && header[0x3E] == (byte) 'E';
    }

    private File getStoredRom() {
        return new File(new File(getFilesDir(), ROM_DIR), ROM_NAME);
    }

    private void launchGame() {
        Intent game = new Intent(this, GameActivity.class);
        startActivity(game);
        finish();
    }

    private void showImportError(String message) {
        progress.setVisibility(View.GONE);
        pickButton.setEnabled(true);
        status.setText("ROM não importada.");
        new AlertDialog.Builder(this)
                .setTitle("ROM inválida")
                .setMessage(message == null ? "Não foi possível importar a ROM." : message)
                .setPositiveButton("Tentar novamente", null)
                .setNegativeButton("Configurações", (dialog, which) -> {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    intent.setData(Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                })
                .show();
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
