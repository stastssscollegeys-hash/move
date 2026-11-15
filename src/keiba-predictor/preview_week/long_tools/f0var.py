import sys, subprocess, numpy as np
def f0s(path):
    raw = subprocess.run(["ffmpeg","-v","error","-i",path,"-t","45","-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32); out=[]
    for i in range(0, len(x)-1024, 512):
        w = x[i:i+1024]
        if np.abs(w).mean() < 500: continue
        w = w - w.mean(); ac = np.correlate(w, w, "full")[1023:]
        lo, hi = 16000//400, 16000//90
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.45*ac[0]: out.append(16000/k)
    return np.array(out), len(x)/16000
for p in sys.argv[1:]:
    f, d = f0s(p); st = 12*np.log2(f/np.median(f))
    print("中央%3.0fHz  高低の幅(10-90%%) %4.1f半音  ばらつき %3.1f半音  %4.1f秒 | %s" % (np.median(f), np.percentile(st,90)-np.percentile(st,10), st.std(), d, p.split("/")[-1][:38]))
