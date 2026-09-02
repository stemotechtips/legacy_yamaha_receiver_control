from .enums import *

def return_int_if_numbers(string):
    if string.lstrip("-").isdecimal():
        return int(string)
    return string

def round_to_nearest_five(number):
    return 5 * round(number / 5)

def input_comparator(input_a, input_b):
    if Input_Type(input_a).value < Input_Type(input_b).value:
        return -1
    elif Input_Type(input_a).value > Input_Type(input_b).value:
        return 1
    else:
        return 0

def audio_setting_comparator(audio_setting_a, audio_setting_b):
    if Audio_Setting_Type(audio_setting_a).value < Audio_Setting_Type(audio_setting_b).value:
        #print(Audio_Setting_Type(audio_setting_a))
        return -1
    elif Audio_Setting_Type(audio_setting_a).value > Audio_Setting_Type(audio_setting_b).value:
        #print(Audio_Setting_Type(audio_setting_b))
        return 1
    else:
        return 0