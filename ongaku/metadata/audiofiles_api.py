import itertools
import json
import os
from pathlib import Path

import mutagen

from ongaku.common.exception import OngakuException
from ongaku.logger import logger
from ongaku.common.metadata import Album, MultiDiscAlbum, Track


class AudioFilesAPI:

    @staticmethod
    def get_albums_from_dir(dirpath: str) -> list[Album]:
        audios = itertools.chain(Path(dirpath).rglob("*.mp3"), Path(dirpath).rglob("*.flac"))
        tags = [AudioFilesAPI.get_audio_tag_standard(a) for a in audios]
        identity = ["album", "catalognumber", "date"]
        sorted_tags = sorted(tags, key=lambda t: tuple(t[key] for key in identity))
        _dict = itertools.groupby(sorted_tags, key=lambda t: tuple(t[key] for key in identity))
        groups = [list(group) for _, group in _dict]
        albums = []
        for group in groups:
            tracks = [Track(title=t["title"], tracknumber=t["tracknumber"], artist=t["artist"]) 
                      for t in group]
            album = Album(album=group[0]["album"], catalognumber=group[0]["catalognumber"], 
                                    date=group[0]["date"], tracks=tracks)
            albums.append(album)
        logger.info(f"Got {len(albums)} albums.")
        return albums

    @staticmethod
    def get_audio_tag(audio: str) -> dict:
        """
        获取音频标签字典。
        raises: OngakuException
        """
        if os.path.splitext(audio)[1].lower() == ".flac":
            return mutagen.flac.FLAC(audio).tags.as_dict()
        elif os.path.splitext(audio)[1].lower() == ".mp3":
            return dict(mutagen.mp3.EasyMP3(audio).tags)
        else:
            logger.error(f"Unsupported audio format. {audio}")
            raise OngakuException()

    @staticmethod
    def get_audio_tag_standard(audio: str) -> dict:
        """
        获取音频标准标签字典。
        1. 仅包含且全包含 [date, catalognumber, album, title, artist, tracknumber] 标签
        2. 多值标签将用 // 连接
        3. 标签默认为空字符串
        raises: OngakuException
        """
        tag, stand_tag = AudioFilesAPI.get_audio_tag(audio), {}
        for stand_k, aks in AudioFilesAPI._TAG_ALIAS.items():
            stand_tag[stand_k] = ""
            for ak in aks:
                vals = tag.get(ak, [])
                vals and stand_tag.update({stand_k: "//".join(vals)})
        logger.debug(f"{json.dumps(stand_tag, ensure_ascii=False)} {audio}")
        return stand_tag

    _TAG_ALIAS = {
        "date": ["date"],
        "catalognumber": ["catalognumber"],
        "album": ["album"],
        "title": ["title"],
        "artist": ["artist"],
        "tracknumber": ["tracknumber"]
    }


















