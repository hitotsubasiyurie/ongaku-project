

## 初始化 数据库

```sh
# 命令行 字符编码 UTF-8
chcp 65001

E:
cd E:\tool\pgsql\bin
set PGDATA=D:\pgdata
set PGCLIENTENCODING=UTF8


# 初始化 数据目录
initdb --auth=trust --encoding=UTF8 --no-locale --nosync

# 启动数据库
pg_ctl start

# 查看状态
pg_ctl status

# 连接数据库
psql -d postgres
psql -d musicbrainz

```


## 创建 表

```sql
-- 创建 musicbrainz
CREATE DATABASE musicbrainz;

-- 进入 musicbrainz
\c musicbrainz

-- 启用扩展 pg_trgm
CREATE EXTENSION pg_trgm;

-- 创建 album
CREATE TABLE album (
    id SERIAL PRIMARY KEY,
    release_id VARCHAR(255) NOT NULL DEFAULT '',
    catalognumber TEXT NOT NULL DEFAULT '',
    date VARCHAR(255) NOT NULL DEFAULT '',
    album TEXT NOT NULL DEFAULT '',
    tracks_json TEXT NOT NULL DEFAULT '',
    links TEXT[] NOT NULL DEFAULT '{}',
    _date_min INTEGER NOT NULL DEFAULT 0,
    _date_max INTEGER NOT NULL DEFAULT 0,
    _tracks_count INTEGER NOT NULL DEFAULT 0,
    _tracks_abstract TEXT NOT NULL DEFAULT ''
);


-- 添加索引
CREATE INDEX idx_album_release_id ON album(release_id);
CREATE INDEX idx_album_catalognumber ON album(catalognumber);
CREATE INDEX idx_album_date ON album(date);
CREATE INDEX idx_album_date_min ON album(_date_min);
CREATE INDEX idx_album_date_max ON album(_date_max);
CREATE INDEX idx_album_tracks_count ON album(_tracks_count);
CREATE INDEX idx_album_catalognumber_trgm ON album USING gin (catalognumber gin_trgm_ops);
CREATE INDEX idx_album_album_trgm ON album USING gin (album gin_trgm_ops);
CREATE INDEX idx_album_tracks_abstract_trgm ON album USING gin (_tracks_abstract gin_trgm_ops);

-- 退出
\q


```


## 查看 表

```sql

-- 扩展显示模式
\x

-- 查询 记录 总数
SELECT count(*) FROM album;


DROP TABLE album;

-- 随机 查看 10 条记录
SELECT * FROM album WHERE random() < 0.01 LIMIT 10;


```



## 备份恢复

```sh
pg_dump -Fc -f d:/musicbrainz.dump musicbrainz

pg_restore -h hostname -U username -d musicbrainz musicbrainz.dump
```


## 搜索

```sh
\x on
\timing on

SELECT *,
       (
         similarity(catalognumber, 'COBC-5991') +
         similarity(album, 'THE IDOLM@STER 5th ANNIVERSARY The world is all one !! 100704 Disc 2 [COBC-5991]')  + 
         similarity(tracks, 'xxxx')
       ) AS match_score
FROM album
ORDER BY match_score DESC
LIMIT 50;


```





