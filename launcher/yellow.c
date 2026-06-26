/*
 * yellow.exe — single-entry launcher that picks the STOCK or EXTENDED
 * recompiled backend at runtime, so the user runs ONE exe and a cfg/env-var
 * decides which Pokemon Yellow they get.
 *
 * Why a wrapper (not one fused binary): gbrecomp is a STATIC recompiler — each
 * backend exe bakes in ONE ROM's code (global func_NNNN symbols, SHA-locked to
 * its ROM). Fusing both would need recompiler symbol-namespacing. This launcher
 * gives the same single-entry-point UX by exec'ing the right backend.
 *
 * Variant resolution (first wins):
 *   1. env  YELLOW_VARIANT = stock | extended
 *   2. file yellow.cfg next to this exe (first line: stock | extended)
 *   3. default: extended
 *
 * Backend lookup (first that exists), relative to this exe's directory:
 *   <dir>\Pokemon_Yellow_<Variant>.exe                       (packaged layout)
 *   <dir>\recomp[_stock]\build\Pokemon_Yellow_<Variant>.exe  (dev build layout)
 *
 * Build:  gcc -O2 -o ../yellow.exe yellow.c     (mingw-w64; no extra libs)
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static void dirname_inplace(char *p) {
    char *b = strrchr(p, '\\');
    char *f = strrchr(p, '/');
    if (f > b) b = f;
    if (b) *b = '\0';
}

static int file_exists(const char *p) {
    DWORD a = GetFileAttributesA(p);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static void trim(char *s) {
    for (char *c = s; *c; c++)
        if (*c == '\n' || *c == '\r' || *c == ' ' || *c == '\t') { *c = '\0'; break; }
}

int main(void) {
    char dir[MAX_PATH];
    GetModuleFileNameA(NULL, dir, MAX_PATH);
    dirname_inplace(dir);                 /* directory of yellow.exe */

    /* 1. resolve variant */
    char variant[64] = {0};
    const char *env = getenv("YELLOW_VARIANT");
    if (env && *env) {
        strncpy(variant, env, sizeof(variant) - 1);
    } else {
        char cfg[MAX_PATH];
        snprintf(cfg, sizeof(cfg), "%s\\yellow.cfg", dir);
        FILE *f = fopen(cfg, "r");
        if (f) { if (!fgets(variant, sizeof(variant), f)) variant[0] = '\0'; fclose(f); }
    }
    trim(variant);
    if (!variant[0]) strcpy(variant, "extended");

    int is_stock = (_stricmp(variant, "stock") == 0);
    const char *Cap = is_stock ? "Stock" : "Extended";
    const char *sub = is_stock ? "recomp_stock" : "recomp";

    /* 2. locate the backend exe */
    char backend[MAX_PATH];
    snprintf(backend, sizeof(backend), "%s\\Pokemon_Yellow_%s.exe", dir, Cap);
    if (!file_exists(backend))
        snprintf(backend, sizeof(backend),
                 "%s\\%s\\build\\Pokemon_Yellow_%s.exe", dir, sub, Cap);
    if (!file_exists(backend)) {
        fprintf(stderr,
                "yellow: no backend for variant '%s' — build it first "
                "(Pokemon_Yellow_%s.exe not found next to yellow.exe or in %s\\build)\n",
                variant, Cap, sub);
        return 2;
    }

    /* 3. forward our command-line tail (everything after argv[0]) */
    const char *cl = GetCommandLineA();
    const char *args = cl;
    if (*args == '"') { args++; while (*args && *args != '"') args++; if (*args) args++; }
    else { while (*args && *args != ' ' && *args != '\t') args++; }
    while (*args == ' ' || *args == '\t') args++;

    char cmd[8192];
    snprintf(cmd, sizeof(cmd), "\"%s\" %s", backend, args);

    /* 4. launch in the backend's own dir; wait; relay its exit code */
    char bdir[MAX_PATH];
    strcpy(bdir, backend);
    dirname_inplace(bdir);

    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi = {0};
    if (!CreateProcessA(NULL, cmd, NULL, NULL, TRUE, 0, NULL, bdir, &si, &pi)) {
        fprintf(stderr, "yellow: failed to launch %s (err %lu)\n",
                backend, (unsigned long)GetLastError());
        return 3;
    }
    fprintf(stderr, "yellow: launching %s variant -> %s\n", Cap, backend);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)code;
}
