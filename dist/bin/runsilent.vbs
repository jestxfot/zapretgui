Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" &""""
cmd = cmd & " --wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=443,50000-50099"
cmd = cmd & " --filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtube.txt"" --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=""tls_clienthello_www_google_com.bin"" --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""discord.txt"" --hostlist=""faceinsta.txt"" --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"
cmd = cmd & " --filter-udp=443 --hostlist=""youtube.txt"" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new"
cmd = cmd & " --filter-udp=50000-50099 --ipset=""ipset-discord.txt"" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""faceinsta.txt"" --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=""tls_clienthello_chat_deepseek_com.bin"""
sh.Run cmd, 0, False          ' 0 = hidden, False = не ждать завершения
