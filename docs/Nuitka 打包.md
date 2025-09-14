
```sh
set http_proxy=http://127.0.0.1:10808
set https_proxy=http://127.0.0.1:10808


```


[nuitka-doc](https://daobook.github.io/nuitka-doc/zh_CN/start.html)

```sh

conda activate env2

cd /d E:\my\ongaku-project-nuitka

set PYTHONPATH=E:\my\ongaku-project

python -m nuitka E:\my\ongaku-project\src\toolkit\main.py --onefile

python -m nuitka E:\my\ongaku-project\src\kanban\main.py --standalone --enable-plugin=pyside6

```

```sh

nuitka --plugin-list






```

