import sys, re, io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open(sys.argv[1], "r", encoding="utf-8", errors="replace").read()
t = re.sub(r"\s+", " ", t)
anchor = "inhabited their traditional territories for approximately 2,000 years"
i = t.find(anchor)
print("anchor at", i)
j = t.find("Notes and references", i)
print("notes at", j)
print(t[j:j+5200])
