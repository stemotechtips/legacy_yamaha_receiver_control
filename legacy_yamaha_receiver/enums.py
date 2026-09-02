from enum import Enum


class Device_Type(Enum):
    OTHER = 0
    RADIO = 1

class Input_Type(Enum):

    SIRIUS = "SIRIUS"
    XM = "XM"
    TUNER = "TUNER"
    MULTI_CH = "MULTI CH"
    PHONO = "PHONO"
    CD = "CD"
    TV = "TV"
    CDR = "MD/CD-R"
    BD = "BD/HD DVD"
    DVD = "DVD"
    CBL_SAT = "CBL/SAT"
    DVR = "DVR"
    VCR = "VCR"
    AUX = "V-AUX"
    DOCK = "DOCK"
    IPOD = "iPod"
    BTH = "Bluetooth"
    PC = "PC/MCX"
    NET_RADIO = "NET RADIO"
    RHAPSODY = "Rhapsody"
    SIRIUS_2 = "SIRIUS InternetRadio"
    USB = "USB"

class Audio_Setting_Type(Enum):

    STRAIGHT = "Straight"
    MUNICH = "Hall in Munich"
    VIENNA = "Hall in Vienna"
    AMSTERDAM = "Hall in Amsterdam"
    FREIBURG = "Church in Freiburg"
    CHAMBER = "Chamber"
    VILLAGE = "Village Vanguard"
    WAREHOUSE = "Warehouse Loft"
    CELLAR = "Cellar Club"
    ROXY = "The Roxy Theatre"
    BOTTOM_LINE = "The Bottom Line"
    SPORTS = "Sports"
    GAME_ACTION = "Action Game"
    GAME_ROLEPLAYING = "Roleplaying Game"
    MUSIC_VIDEO = "Music Video"
    OPERA = "Recital/Opera"
    STANDARD = "Standard"
    SPECTACLE = "Spectacle"
    SCIFI = "Sci-Fi"
    ADVENTURE = "Adventure"
    DRAMA = "Drama"
    MONO_MOVIE = "Mono Movie"
    STEREO_TWOCH = "2ch Stereo"
    STEREO_SEVENCH = "7ch Stereo"
    STEREO_NINECH = "9ch Stereo"
    ENHANCER_STRAIGHT = "Straight Enhancer"
    ENHANCER_7CH = "7ch Enhancer"
    ENHANCER_9CH = "9ch Enhancer"
    SURROUND_DECODE = "Surround Decode"
