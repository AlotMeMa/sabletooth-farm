"""3.17: починить рецепт pygame в python-for-android перед сборкой APK.

    python mobile/patch_p4a.py <папка python-for-android>

Известная беда (kivy/python-for-android#3405): в Android-сборке модуля surface не хватает файлов
simd_blitters_*.c, и APK падает при запуске (cannot locate symbol "alphablit_alpha_sse2_argb_surf_alpha" /
"pg_has_avx2"). Добавляем их в шаблон Setup.Android.SDL2.in, если их там ещё нет. Повторный запуск ничего не портит.
"""
import os
import sys

MARK = "# 3.17 vesyolaya-ferma: simd blitters"
FIX = ('{ind}if "simd_blitters" not in setup_template:  ' + MARK + '\n'
       '{ind}    setup_template = setup_template.replace("surface src_c/surface.c", '
       '"surface src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c src_c/surface.c")\n')


def main(p4a):
    path = os.path.join(p4a, "pythonforandroid", "recipes", "pygame", "__init__.py")
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    if any(MARK in ln for ln in lines):
        print("рецепт pygame уже исправлен")
        return
    for i, ln in enumerate(lines):
        if "Setup.Android.SDL2.in" in ln and "setup_template" in ln and "=" in ln:
            ind = ln[:len(ln) - len(ln.lstrip())]
            lines.insert(i + 1, FIX.format(ind=ind))
            break
    else:
        sys.exit("Не нашёл в рецепте pygame строку с Setup.Android.SDL2.in — рецепт поменялся, смотри его глазами")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("рецепт pygame исправлен:", path)


if __name__ == "__main__":
    main(sys.argv[1])
