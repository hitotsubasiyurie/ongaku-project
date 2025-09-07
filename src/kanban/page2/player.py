from mtags import *
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtWidgets import QApplication,QWidget,QSlider,QStyleFactory,\
    QTableWidget,QTableWidgetItem,QPushButton,QLabel
from PySide6.QtGui import QResizeEvent,QColor,QKeyEvent,QBrush
from PySide6.QtCore import Qt,QBuffer, QIODevice,QUrl
import subprocess
import time
import pynput

Xname='电波'
inDirpath=Path(fr'D:\移动云盘同步盘\ongaku-resource')
outDirpath=Path(fr'D:\同步文件夹\同步盘\音乐\{Xname}')
hispath=inDirpath/'history.txt'
ffmpeg_exe=r'E:\tool\ffmpeg\bin\ffmpeg.exe'

def convert_to_wav_bytes(songpath):
    '''调用ffmpeg 转成wav字节流'''
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(
        args=[ffmpeg_exe,'-i',songpath,'-f', 'wav', 'pipe:1'],
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startup_info
    )
    stdout, stderr = process.communicate()
    return stdout

class Main(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.setGeometry(0,0,DW,DH)
        self.setWindowTitle(Xname)
        self.setStyleSheet("font-size:13px;")
        self._assests()
        self._actions()
        self._geometry()
        self.load_Atable()
        self.load_history()
        self.changeCurrent(self.current)

    def _assests(self):
        self.Output=QAudioOutput(self)
        self.Player=QMediaPlayer(self)
        self.Player.setAudioOutput(self.Output)
        self.Player.setLoops(-1)
        self.buffer = QBuffer()

        self.keyController=pynput.keyboard.Controller()

        self.Atable=QTableWidget(self)
        header=self.Atable.horizontalHeader()
        header.setVisible(False)
        header=self.Atable.verticalHeader()
        header.setVisible(False)
        self.Atable.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.Atable.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.Atable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.Atable.setColumnCount(5)
        
        self.Cslider=QSlider(self)
        self.Cslider.setOrientation(Qt.Orientation.Horizontal)
        self.Cslider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.CsliderPressing=False

        self.Ctime=QLabel(self)
        self.Ctime.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignHCenter)
        self.Ctime.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.Cctrl=QPushButton('ALT',self)
        self.Cctrl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.Cnext=QPushButton('NEXT',self)
        self.Cnext.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.Clove=QPushButton('LOVE',self)
        self.Clove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.Cmtags=QPushButton('mtags',self)
        self.Cmtags.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _geometry(self):
        w,h=self.width(),self.height()
        x=150
        y=30
        self.Atable.setGeometry(0,0,w,h-y)
        self.Cslider.setGeometry(0,self.Atable.height(),w-y*8,y)
        self.Ctime.setGeometry(self.Cslider.geometry())
    
        self.Cctrl.setGeometry(w-y*8,self.Atable.height(),y*2,y)
        self.Clove.setGeometry(w-y*6,self.Atable.height(),y*2,y)
        self.Cnext.setGeometry(w-y*4,self.Atable.height(),y*2,y)
        self.Cmtags.setGeometry(w-y*2,self.Atable.height(),y*2,y)

    def _actions(self):
        self.Player.positionChanged.connect(self.on_Player_positionChanged)
        self.Atable.cellDoubleClicked.connect(self.on_Atable_cellDoubleClicked)

        self.Cslider.sliderPressed.connect(lambda:setattr(self,'CsliderPressing',True))
        self.Cslider.sliderReleased.connect(lambda:setattr(self,'CsliderPressing',False))
        self.Cslider.valueChanged.connect(self.on_Cslider_valueChanged)
            
        self.Cctrl.clicked.connect(self.on_Cctrl_clicked)
        self.Cnext.clicked.connect(lambda: self.changeCurrent(self.current+1))
        self.Clove.clicked.connect(self.on_Clove_clicked)
        self.Cmtags.clicked.connect(self.on_Cmtags_clicked)

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        '''键盘命令'''
        if a0.key()==Qt.Key.Key_Space:
            if self.Player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:
                self.Player.pause()
            else:
                self.Player.play()
        elif a0.key()==Qt.Key.Key_Left:
            self.Player.setPosition(self.Player.position()-3000)
        elif a0.key()==Qt.Key.Key_Right:
            self.Player.setPosition(self.Player.position()+3000)
        elif a0.key()==Qt.Key.Key_Up:
            self.keyController.press(pynput.keyboard.Key.media_volume_up)
        elif a0.key()==Qt.Key.Key_Down:
            self.keyController.press(pynput.keyboard.Key.media_volume_down)
        elif a0.key()==Qt.Key.Key_Backspace:
            self.Player.setPosition(0)
        elif a0.key()==Qt.Key.Key_NumLock:
            self.on_Clove_clicked()
        elif a0.key()==Qt.Key.Key_Control and self.Cctrl.text()=='CTRL':
            self.changeCurrent(self.current+1)
        elif a0.key()==Qt.Key.Key_Alt and self.Cctrl.text()=='ALT':
            self.changeCurrent(self.current+1)
        elif self.Cctrl.text()=='*':
            self.changeCurrent(self.current+1)
        return super().keyPressEvent(a0)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self._geometry()

    def add_song_to_Atable(self,row:int,songpath:Path):
        '''添加'''
        tags=read_base_songtags(songpath)
        item=QTableWidgetItem(str('{:.2f}'.format(songpath.stat().st_size/1024/1024))+' MB')
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.Atable.setItem(row,0,item)
        item=QTableWidgetItem(songpath.suffix)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.Atable.setItem(row,1,item)
        self.Atable.setItem(row,2,QTableWidgetItem(r'\\'.join(tags['标题'])))
        self.Atable.setItem(row,3,QTableWidgetItem(r'\\'.join(tags['艺术家'])))
        self.Atable.setItem(row,4,QTableWidgetItem(r'\\'.join(tags['专辑'])))

    def load_Atable(self):
        '''加载Atable'''
        self.songpaths=[p for p in list(Path(inDirpath).rglob('*')) if str(p).endswith(('.flac','.mp3'))]
        self.songpaths.sort(key=lambda x:x.name.upper())
        aw=self.Atable.width()
        self.Atable.setColumnWidth(0,aw//20)
        self.Atable.setColumnWidth(1,aw//20)
        self.Atable.setColumnWidth(2,aw//20*5)
        self.Atable.setColumnWidth(3,aw//20*8)
        self.Atable.setColumnWidth(4,aw//20*5)
        self.Atable.setRowCount(len(self.songpaths))
        [self.Atable.setRowHeight(i,14) for i in range(len(self.songpaths))]
        for i in range(len(self.songpaths)):
            self.add_song_to_Atable(i,self.songpaths[i])

    def load_history(self):
        '''加载历史'''
        self.current=0
        self.history=[]
        if hispath.exists():
            self.history=[line for line in hispath.read_text(encoding='utf-8').split('\n') if line]
            for i in range(len(self.songpaths)):
                if str(self.songpaths[i]) in self.history:
                    self.lowlight_Atable_row(i)
                    self.current=i
                
    def changeCurrent(self,next:int):
        '''记录current 播放next'''
        if str(self.songpaths[self.current]) not in self.history:
            self.history.append(str(self.songpaths[self.current]))
            with hispath.open('a',encoding='utf-8') as f:
                f.write(str(self.songpaths[self.current])+'\n')
        if next>0:
            self.lowlight_Atable_row(self.current)
        self.current=next
        if self.current < len(self.songpaths):
            self.highlight_Atable_row(self.current)
            self.playCurrent()
        else:
            os.remove(hispath)
            exit(0)

    def playCurrent(self):
        '''播放当前歌曲'''
        wavbytes=convert_to_wav_bytes(self.songpaths[self.current])
        self.Player.stop()
        time.sleep(0.01) # 等待0.01秒
        self.Player.setSource(QUrl())
        self.buffer.close()
        self.buffer.setData(wavbytes)
        self.buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.Player.setSourceDevice(self.buffer)
        self.Player.play()

    def highlight_Atable_row(self,row):
        '''高光 Atable row'''
        [self.Atable.item(row,i).setBackground(QColor( 21, 67, 96  )) for i in range(5)]
        self.Atable.scrollToItem(self.Atable.item(row,0),QTableWidget.ScrollHint.PositionAtCenter)
        self.Atable.scrollToItem(self.Atable.item(row,0),QTableWidget.ScrollHint.PositionAtCenter)

    def lowlight_Atable_row(self,row):
        '''低光 Atable row'''
        [self.Atable.item(row,i).setForeground(QColor( 98, 101, 103  )) for i in range(5)]
        [self.Atable.item(row,i).setBackground(QBrush()) for i in range(5)]

    def on_Player_positionChanged(self,pos:int):
        if not self.CsliderPressing:
            pos=self.Player.position()//1000
            dur=self.Player.duration()//1000
            self.Cslider.setValue(100*pos//dur)
            self.Ctime.setText(f'{self.current+1}/{len(self.songpaths)+1}{" "*8}{pos}/{dur}')

    def on_Cslider_valueChanged(self,value:int):
        if self.CsliderPressing:
            self.Player.setPosition(self.Player.duration()*value//100)

    def on_Atable_cellDoubleClicked(self,row,col):
        if col==0:
            self.changeCurrent(next=row)
        if col==1:
            os.startfile(self.songpaths[row].parent)

    def on_Cctrl_clicked(self):
        if self.Cctrl.text()=='CTRL':
            self.Cctrl.setText('ALT')
        elif self.Cctrl.text()=='ALT':
            self.Cctrl.setText('*')
        elif self.Cctrl.text()=='*':
            self.Cctrl.setText('CTRL')

    def on_Clove_clicked(self):
        '''复制歌曲'''
        outDirpath.mkdir(exist_ok=True)
        songpath=self.songpaths[self.current]
        newpath=outDirpath/songpath.name
        if not newpath.exists():
            newpath.touch()
            newpath.write_bytes(songpath.read_bytes())
        [self.Atable.item(self.current,i).setBackground(QColor( 130, 224, 170   )) for i in range(5)]

    def on_Cmtags_clicked(self):
        '''修改标签'''
        tags={
            '标题':re.split(r'[;]|\\\\',self.Atable.item(self.current,2).text()),
            '艺术家':re.split(r'[;]|\\\\',self.Atable.item(self.current,3).text()),
            '专辑':re.split(r'[;]|\\\\',self.Atable.item(self.current,4).text()),
        }
        write_base_songtags(str(self.songpaths[self.current]),tags)
        self.songpaths[self.current]=rename_song(self.songpaths[self.current])
        self.add_song_to_Atable(self.current,self.songpaths[self.current])
        self.highlight_Atable_row(self.current)

if __name__=='__main__':
    APP = QApplication([])
    APP.setStyle(QStyleFactory.create('Fusion'))
    DW=APP.screens()[0].availableVirtualSize().width()
    DH=APP.screens()[0].availableVirtualSize().height()
    main=Main()
    main.showMaximized()
    APP.exec()

