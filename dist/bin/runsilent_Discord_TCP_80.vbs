Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" & """"
cmd = cmd & " --wf-tcp=80,443 --wf-udp=443,50000-59000"
cmd = cmd & " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=""quic_test_00.bin"" --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtubeGV.txt"" --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4 --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtube.txt"" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=""tls_clienthello_www_google_com.bin"" --dpi-desync-ttl=3 --new"
cmd = cmd & " --filter-tcp=80 --hostlist=""discord.txt"" --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new"
cmd = cmd & " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=""quic_1.bin"" --new"
cmd = cmd & " --filter-udp=50000-59000 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""discord.txt"" --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=""tls_clienthello_4.bin"" --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""faceinsta.txt"" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=""tls_clienthello_3.bin"" --dpi-desync-ttl=2"
sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
