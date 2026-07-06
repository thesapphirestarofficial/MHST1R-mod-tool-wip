from pathlib import Path
import struct

IMAGE_BASE=0x400000
FILE_ALIGN=0x200
SECT_ALIGN=0x1000
TEXT_RVA=0x1000; TEXT_RAW=0x200
RDATA_RVA=0x2000; RDATA_RAW=0x400

def align(n,a): return (n+a-1)//a*a

def put(b,off,data): b[off:off+len(data)] = data

def u16(x): return struct.pack('<H',x)
def u32(x): return struct.pack('<I',x)

# rdata layout
cmd = b'powershell -NoProfile -ExecutionPolicy Bypass -File MHST1ModLoader.ps1\x00'
kernel = b'KERNEL32.dll\x00'
hn_winexec = u16(0)+b'WinExec\x00'
hn_exit = u16(0)+b'ExitProcess\x00'

o_cmd=0x000
o_kernel=align(o_cmd+len(cmd),2)
o_hn_win=align(o_kernel+len(kernel),2)
o_hn_exit=align(o_hn_win+len(hn_winexec),2)
o_int=align(o_hn_exit+len(hn_exit),4)
o_iat=o_int+12
o_desc=o_iat+12
r_cmd=RDATA_RVA+o_cmd
r_kernel=RDATA_RVA+o_kernel
r_hn_win=RDATA_RVA+o_hn_win
r_hn_exit=RDATA_RVA+o_hn_exit
r_int=RDATA_RVA+o_int
r_iat=RDATA_RVA+o_iat
r_desc=RDATA_RVA+o_desc

# x86 code: push 1; push cmdVA; call [iat WinExec]; push 0; call [iat ExitProcess]
code = b'\x6A\x01' + b'\x68' + u32(IMAGE_BASE+r_cmd) + b'\xFF\x15' + u32(IMAGE_BASE+r_iat) + b'\x6A\x00' + b'\xFF\x15' + u32(IMAGE_BASE+r_iat+4)
entry_rva=TEXT_RVA

text_raw=bytearray(FILE_ALIGN); put(text_raw,0,code)
rdata_raw=bytearray(FILE_ALIGN)
put(rdata_raw,o_cmd,cmd); put(rdata_raw,o_kernel,kernel); put(rdata_raw,o_hn_win,hn_winexec); put(rdata_raw,o_hn_exit,hn_exit)
# INT and IAT arrays
put(rdata_raw,o_int,u32(r_hn_win)+u32(r_hn_exit)+u32(0))
put(rdata_raw,o_iat,u32(r_hn_win)+u32(r_hn_exit)+u32(0))
# import descriptor + null descriptor
put(rdata_raw,o_desc,u32(r_int)+u32(0)+u32(0)+u32(r_kernel)+u32(r_iat)+bytes(20))

headers=bytearray(TEXT_RAW)
# DOS header
put(headers,0,b'MZ'); put(headers,0x3c,u32(0x80))
# PE signature
pe=0x80; put(headers,pe,b'PE\0\0')
# COFF
put(headers,pe+4,u16(0x14c)+u16(2)+u32(0)+u32(0)+u32(0)+u16(0xE0)+u16(0x010F))
opt=pe+24
# Optional PE32
put(headers,opt,u16(0x10b))
headers[opt+2]=8; headers[opt+3]=0
put(headers,opt+4,u32(len(text_raw)))
put(headers,opt+8,u32(len(rdata_raw)))
put(headers,opt+16,u32(entry_rva))
put(headers,opt+20,u32(TEXT_RVA))
put(headers,opt+24,u32(RDATA_RVA))
put(headers,opt+28,u32(IMAGE_BASE))
put(headers,opt+32,u32(SECT_ALIGN)); put(headers,opt+36,u32(FILE_ALIGN))
put(headers,opt+40,u16(4)+u16(0)+u16(0)+u16(0)+u16(4)+u16(0))
put(headers,opt+56,u32(0x3000)) # SizeOfImage
put(headers,opt+60,u32(TEXT_RAW)) # SizeOfHeaders
put(headers,opt+68,u16(3)) # subsystem console
put(headers,opt+72,u32(0x100000)); put(headers,opt+76,u32(0x1000)); put(headers,opt+80,u32(0x100000)); put(headers,opt+84,u32(0x1000))
put(headers,opt+92,u32(16)) # dirs
# import directory index 1
put(headers,opt+96+8,u32(r_desc)+u32(40))
# sections
sec=opt+0xE0
def section(off,name,vs,va,rawsize,rawptr,chars):
    put(headers,off,name.ljust(8,b'\0')+u32(vs)+u32(va)+u32(rawsize)+u32(rawptr)+u32(0)+u32(0)+u16(0)+u16(0)+u32(chars))
section(sec,b'.text',len(code),TEXT_RVA,len(text_raw),TEXT_RAW,0x60000020)
section(sec+40,b'.rdata',len(rdata_raw),RDATA_RVA,len(rdata_raw),RDATA_RAW,0x40000040)

out=headers+text_raw+rdata_raw
Path('MHST1ModLoader.exe').write_bytes(out)
print('wrote MHST1ModLoader.exe',len(out),'bytes')
