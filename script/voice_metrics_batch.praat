form Voice metrics batch
  sentence audio_path
  sentence out_file
endform

f0min = 75
f0max = 500

# 넘어온 audio_path 가 폴더든 파일이든, 그 안/같은 폴더의 모든 wav를 순회한다.
# 1) 끝에 구분자가 있으면 그대로 폴더로 사용
# 2) 없으면, .wav 로 끝나는 파일 경로면 부모 폴더를, 아니면 폴더로 간주하고 구분자를 붙임
last$ = right$(audio_path$, 1)
if last$ = "\" or last$ = "/"
  folder$ = audio_path$
else
  ext$ = right$(audio_path$, 4)
  if ext$ = ".wav" or ext$ = ".WAV"
    slash = rindex(audio_path$, "\")
    if slash = 0
      slash = rindex(audio_path$, "/")
    endif
    folder$ = left$(audio_path$, slash)
  else
    folder$ = audio_path$ + "\"
  endif
endif

strings = Create Strings as file list: "list", folder$ + "*.wav"
n = Get number of strings

header$ = "file" + tab$ + "dur_s" + tab$
  ... + "F0_mean_Hz" + tab$ + "F0_sd_Hz" + tab$ + "F0_min_Hz" + tab$ + "F0_max_Hz" + tab$
  ... + "Intensity_mean_dB" + tab$ + "Intensity_sd_dB" + tab$ + "Intensity_min_dB" + tab$ + "Intensity_max_dB" + tab$
  ... + "CPP_mean_dB" + tab$
  ... + "HNR_mean_dB" + tab$ + "HNR_sd_dB"
writeFileLine: out_file$, header$
appendInfoLine: "folder = ", folder$
appendInfoLine: header$

for i to n
  selectObject: strings
  name$ = Get string: i
  snd = Read from file: folder$ + name$
  dur = Get total duration

  # ---------- F0 (pitch) ----------
  selectObject: snd
  pitch = To Pitch: 0, f0min, f0max
  f0mean = Get mean: 0, 0, "Hertz"
  f0sd   = Get standard deviation: 0, 0, "Hertz"
  f0min_v = Get minimum: 0, 0, "Hertz", "Parabolic"
  f0max_v = Get maximum: 0, 0, "Hertz", "Parabolic"
  removeObject: pitch

  # ---------- Intensity ----------
  selectObject: snd
  intensity = To Intensity: f0min, 0, "yes"
  int_mean = Get mean: 0, 0, "energy"
  int_sd   = Get standard deviation: 0, 0
  int_min  = Get minimum: 0, 0, "Parabolic"
  int_max  = Get maximum: 0, 0, "Parabolic"
  removeObject: intensity

  # ---------- HNR (harmonicity) ----------
  selectObject: snd
  harm = To Harmonicity (cc): 0.01, f0min, 0.1, 1.0
  hnr_mean = Get mean: 0, 0
  hnr_sd   = Get standard deviation: 0, 0
  removeObject: harm

  # ---------- CPP (smoothed cepstral peak prominence) ----------
  selectObject: snd
  pcg = To PowerCepstrogram: f0min, 0.002, 5000, 50
  cpp = Get CPPS: "yes", 0.02, 0.0005, f0min, f0max, 0.05, "Parabolic", 0.001, 0, "Exponential decay", "Robust slow"
  removeObject: pcg

  # ---------- 한 줄 기록 ----------
  line$ = name$ + tab$
    ... + fixed$(dur, 3) + tab$
    ... + fixed$(f0mean, 2) + tab$ + fixed$(f0sd, 2) + tab$ + fixed$(f0min_v, 2) + tab$ + fixed$(f0max_v, 2) + tab$
    ... + fixed$(int_mean, 2) + tab$ + fixed$(int_sd, 2) + tab$ + fixed$(int_min, 2) + tab$ + fixed$(int_max, 2) + tab$
    ... + fixed$(cpp, 3) + tab$
    ... + fixed$(hnr_mean, 3) + tab$ + fixed$(hnr_sd, 3)
  appendFileLine: out_file$, line$
  appendInfoLine: line$

  removeObject: snd
endfor

removeObject: strings
appendInfoLine: "DONE: ", n, " files analyzed."
