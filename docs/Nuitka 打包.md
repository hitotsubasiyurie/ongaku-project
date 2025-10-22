
```sh
set http_proxy=http://127.0.0.1:10808
set https_proxy=http://127.0.0.1:10808


```


[nuitka-doc](https://daobook.github.io/nuitka-doc/zh_CN/start.html)

```sh

conda activate ongaku

cd /d E:\my\ongaku-project

set PYTHONPATH=.

python -m nuitka .\ongaku\kanban_ui\main.py ^
--standalone ^
--enable-plugin=pyside6 ^
--include-data-dir=.\ongaku\kanban_ui\assets=assets ^
--windows-icon-from-ico=.\ongaku\kanban_ui\assets\icon.png ^
--output-filename=kanban.exe ^
--force-stdout-spec={PROGRAM_BASE}.out.txt ^
--force-stderr-spec={PROGRAM_BASE}.err.txt ^
--output-dir=..\ongaku-build
--include-qt-plugins=multimedia ^
--windows-console-mode=disable ^




python -m nuitka .\ongaku\toolkit\main.py ^
--standalone ^
--include-package=ongaku.toolkit.plugin ^
--windows-icon-from-ico=.\ongaku\kanban_ui\assets\cmd.png ^
--output-filename=toolkit.exe ^
--force-stdout-spec={PROGRAM_BASE}.out.txt ^
--force-stderr-spec={PROGRAM_BASE}.err.txt ^
--output-dir=..\ongaku-build-toolkit





```

```sh

nuitka --plugin-list






```

