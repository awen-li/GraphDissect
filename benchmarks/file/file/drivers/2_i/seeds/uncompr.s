	.text
	.file	"uncompr.c"
	.file	0 "/home/awen/git/DSGFuzz/benchmarks/binutils/build/zlib" "uncompr.c" md5 0x58c519816a08870e3ccdec3bd4141039
	.file	1 "../../binutils-2.44/zlib" "zconf.h"
	.file	2 "../../binutils-2.44/zlib" "zlib.h"
	.globl	uncompress2                     # -- Begin function uncompress2
	.p2align	4, 0x90
	.type	uncompress2,@function
uncompress2:                            # @uncompress2
.Lfunc_begin0:
	.file	3 "../../binutils-2.44/zlib" "uncompr.c"
	.loc	3 32 0                          # ../../binutils-2.44/zlib/uncompr.c:32:0
	.cfi_startproc
# %bb.0:                                # %entry
	#DEBUG_VALUE: uncompress2:dest <- $rdi
	#DEBUG_VALUE: uncompress2:destLen <- $rsi
	#DEBUG_VALUE: uncompress2:source <- $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- $rcx
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	subq	$152, %rsp
	.cfi_offset %rbx, -56
	.cfi_offset %r12, -48
	.cfi_offset %r13, -40
	.cfi_offset %r14, -32
	.cfi_offset %r15, -24
	movq	%rcx, %r13
	movq	%rdx, %r12
	movq	%rsi, %rbx
	movq	%rdi, -56(%rbp)                 # 8-byte Spill
.Ltmp0:
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	.loc	3 32 0 prologue_end             # ../../binutils-2.44/zlib/uncompr.c:32:0
	callq	mcount@PLT
.Ltmp1:
	#DEBUG_VALUE: uncompress2:sourceLen <- $r13
	#DEBUG_VALUE: uncompress2:source <- $r12
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:max <- -1
	.loc	3 39 11                         # ../../binutils-2.44/zlib/uncompr.c:39:11
	movq	(%r13), %r14
.Ltmp2:
	#DEBUG_VALUE: uncompress2:len <- $r14
	.loc	3 40 9                          # ../../binutils-2.44/zlib/uncompr.c:40:9
	movq	(%rbx), %r15
	testq	%r15, %r15
.Ltmp3:
	.loc	3 40 9 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:40:9
	je	.LBB0_2
.Ltmp4:
# %bb.1:                                # %if.then
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- $r12
	#DEBUG_VALUE: uncompress2:sourceLen <- $r13
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 42 18 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:42:18
	movq	$0, (%rbx)
	jmp	.LBB0_3
.Ltmp5:
.LBB0_2:
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- $r12
	#DEBUG_VALUE: uncompress2:sourceLen <- $r13
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	.loc	3 0 18 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:0:18
	leaq	-41(%rbp), %rax
	movq	%rax, -56(%rbp)                 # 8-byte Spill
.Ltmp6:
	#DEBUG_VALUE: uncompress2:dest <- undef
	movl	$1, %r15d
.Ltmp7:
.LBB0_3:                                # %if.end
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_LLVM_entry_value 1] $rdi
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- $r12
	#DEBUG_VALUE: uncompress2:sourceLen <- $r13
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	.loc	3 49 20 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:49:20
	movq	%r12, -184(%rbp)
	.loc	3 50 21                         # ../../binutils-2.44/zlib/uncompr.c:50:21
	movl	$0, -176(%rbp)
	.loc	3 51 19                         # ../../binutils-2.44/zlib/uncompr.c:51:19
	xorps	%xmm0, %xmm0
	movups	%xmm0, -120(%rbp)
	movq	$0, -104(%rbp)
	leaq	-184(%rbp), %rdi
	.loc	3 55 11                         # ../../binutils-2.44/zlib/uncompr.c:55:11
	movl	$.L.str, %esi
	movl	$112, %edx
	callq	inflateInit_
.Ltmp8:
	#DEBUG_VALUE: uncompress2:err <- $eax
	.loc	3 56 13                         # ../../binutils-2.44/zlib/uncompr.c:56:13
	testl	%eax, %eax
.Ltmp9:
	.loc	3 56 9 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:56:9
	je	.LBB0_5
.Ltmp10:
.LBB0_4:                                # %cleanup
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_LLVM_entry_value 1] $rsi
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_LLVM_entry_value 1] $rcx
	#DEBUG_VALUE: uncompress2:max <- -1
	.loc	3 84 1 is_stmt 1                # ../../binutils-2.44/zlib/uncompr.c:84:1
	addq	$152, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_def_cfa %rsp, 8
	retq
.Ltmp11:
.LBB0_5:                                # %if.end2
	.cfi_def_cfa %rbp, 16
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- $r12
	#DEBUG_VALUE: uncompress2:sourceLen <- $r13
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $eax
	.loc	3 0 1 is_stmt 0                 # ../../binutils-2.44/zlib/uncompr.c:0:1
	movq	%r13, -72(%rbp)                 # 8-byte Spill
.Ltmp12:
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	movq	%rbx, -64(%rbp)                 # 8-byte Spill
.Ltmp13:
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	movl	$4294967295, %r12d              # imm = 0xFFFFFFFF
.Ltmp14:
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	movq	-56(%rbp), %rax                 # 8-byte Reload
.Ltmp15:
	#DEBUG_VALUE: uncompress2:dest <- $rax
	.loc	3 58 21 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:58:21
	movq	%rax, -160(%rbp)
	.loc	3 59 22                         # ../../binutils-2.44/zlib/uncompr.c:59:22
	movl	$0, -152(%rbp)
	xorl	%eax, %eax
.Ltmp16:
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	.loc	3 0 22 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:0:22
	leaq	-184(%rbp), %r13
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:len <- $r14
.Ltmp17:
	.loc	3 62 30 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:62:30
	testl	%eax, %eax
	jne	.LBB0_6
	jmp	.LBB0_9
.Ltmp18:
	.p2align	4, 0x90
.LBB0_8:                                # %do.bodythread-pre-split
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $eax
	.loc	3 62 20 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:62:20
	movl	-152(%rbp), %eax
.Ltmp19:
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:len <- $r14
	.loc	3 62 30                         # ../../binutils-2.44/zlib/uncompr.c:62:30
	testl	%eax, %eax
.Ltmp20:
	.loc	3 62 13                         # ../../binutils-2.44/zlib/uncompr.c:62:13
	jne	.LBB0_6
.Ltmp21:
.LBB0_9:                                # %if.then5
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 63 32 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:63:32
	cmpq	%r12, %r15
	movl	$4294967295, %eax               # imm = 0xFFFFFFFF
	cmovbq	%r15, %rax
	.loc	3 63 30 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:63:30
	movl	%eax, -152(%rbp)
	.loc	3 64 18 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:64:18
	subq	%rax, %r15
.Ltmp22:
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 66 29                         # ../../binutils-2.44/zlib/uncompr.c:66:29
	cmpl	$0, -176(%rbp)
.Ltmp23:
	.loc	3 66 13 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:66:13
	jne	.LBB0_7
.Ltmp24:
.LBB0_10:                               # %if.then14
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 67 31 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:67:31
	cmpq	%r12, %r14
	movl	$4294967295, %eax               # imm = 0xFFFFFFFF
	cmovbq	%r14, %rax
	.loc	3 67 29 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:67:29
	movl	%eax, -176(%rbp)
	.loc	3 68 17 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:68:17
	subq	%rax, %r14
.Ltmp25:
	#DEBUG_VALUE: uncompress2:len <- $r14
	.loc	3 0 17 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:0:17
	jmp	.LBB0_7
.Ltmp26:
	.p2align	4, 0x90
.LBB0_6:                                # %if.end10
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 66 29 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:66:29
	cmpl	$0, -176(%rbp)
.Ltmp27:
	.loc	3 66 13 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:66:13
	je	.LBB0_10
.Ltmp28:
.LBB0_7:                                # %if.end26
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:len <- $r14
	.loc	3 70 15 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:70:15
	movq	%r13, %rdi
	xorl	%esi, %esi
	callq	inflate
.Ltmp29:
	#DEBUG_VALUE: uncompress2:err <- $eax
	.loc	3 71 18                         # ../../binutils-2.44/zlib/uncompr.c:71:18
	testl	%eax, %eax
.Ltmp30:
	.loc	3 71 5 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:71:5
	je	.LBB0_8
.Ltmp31:
# %bb.11:                               # %do.end
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- $rbx
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:len <- $r14
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $eax
	.loc	3 0 0                           # ../../binutils-2.44/zlib/uncompr.c:0:0
	movl	%eax, %ebx
.Ltmp32:
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	.loc	3 73 32 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:73:32
	movl	-176(%rbp), %eax
.Ltmp33:
	#DEBUG_VALUE: uncompress2:err <- $ebx
	.loc	3 73 23 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:73:23
	addq	%rax, %r14
.Ltmp34:
	.loc	3 0 23                          # ../../binutils-2.44/zlib/uncompr.c:0:23
	movq	-72(%rbp), %rax                 # 8-byte Reload
.Ltmp35:
	#DEBUG_VALUE: uncompress2:sourceLen <- $rax
	.loc	3 73 16                         # ../../binutils-2.44/zlib/uncompr.c:73:16
	subq	%r14, (%rax)
	leaq	-41(%rbp), %rcx
.Ltmp36:
	.loc	3 0 0                           # ../../binutils-2.44/zlib/uncompr.c:0:0
	movq	-144(%rbp), %rax
.Ltmp37:
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	.loc	3 74 14 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:74:14
	cmpq	%rcx, -56(%rbp)                 # 8-byte Folded Reload
.Ltmp38:
	.loc	3 74 9 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:74:9
	je	.LBB0_13
.Ltmp39:
# %bb.12:                               # %if.then36
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	.loc	3 0 9                           # ../../binutils-2.44/zlib/uncompr.c:0:9
	movq	-64(%rbp), %rcx                 # 8-byte Reload
.Ltmp40:
	#DEBUG_VALUE: uncompress2:destLen <- $rcx
	.loc	3 75 18 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:75:18
	movq	%rax, (%rcx)
	jmp	.LBB0_14
.Ltmp41:
.LBB0_13:                               # %if.else37
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	.loc	3 0 18 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:0:18
	cmpl	$-5, %ebx
	movl	$1, %ecx
.Ltmp42:
	.loc	3 76 31 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:76:31
	cmovneq	%r15, %rcx
	.loc	3 76 14 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:76:14
	testq	%rax, %rax
	.loc	3 76 31                         # ../../binutils-2.44/zlib/uncompr.c:76:31
	cmovneq	%rcx, %r15
.Ltmp43:
.LBB0_14:                               # %if.end44
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:err <- $ebx
	#DEBUG_VALUE: uncompress2:left <- $r15
	.loc	3 0 31                          # ../../binutils-2.44/zlib/uncompr.c:0:31
	leaq	-184(%rbp), %rdi
	.loc	3 79 5 is_stmt 1                # ../../binutils-2.44/zlib/uncompr.c:79:5
	callq	inflateEnd
.Ltmp44:
	.loc	3 80 12                         # ../../binutils-2.44/zlib/uncompr.c:80:12
	cmpl	$2, %ebx
	je	.LBB0_19
.Ltmp45:
# %bb.15:                               # %if.end44
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	cmpl	$1, %ebx
	je	.LBB0_20
.Ltmp46:
# %bb.16:                               # %if.end44
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	cmpl	$-5, %ebx
	jne	.LBB0_21
.Ltmp47:
# %bb.17:                               # %land.lhs.true56
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	.loc	3 82 41                         # ../../binutils-2.44/zlib/uncompr.c:82:41
	movl	-152(%rbp), %ecx
	movl	$-3, %eax
	.loc	3 82 32 is_stmt 0               # ../../binutils-2.44/zlib/uncompr.c:82:32
	addq	%rcx, %r15
.Ltmp48:
	.loc	3 82 12                         # ../../binutils-2.44/zlib/uncompr.c:82:12
	jne	.LBB0_4
.Ltmp49:
.LBB0_21:
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:err <- $ebx
	.loc	3 0 12                          # ../../binutils-2.44/zlib/uncompr.c:0:12
	movl	%ebx, %eax
	jmp	.LBB0_4
.Ltmp50:
.LBB0_19:                               # %cond.end67.fold.split
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	movl	$-3, %eax
	jmp	.LBB0_4
.Ltmp51:
.LBB0_20:
	#DEBUG_VALUE: uncompress2:dest <- [DW_OP_constu 56, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:destLen <- [DW_OP_constu 64, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:source <- [DW_OP_LLVM_entry_value 1] $rdx
	#DEBUG_VALUE: uncompress2:sourceLen <- [DW_OP_constu 72, DW_OP_minus] [$rbp+0]
	#DEBUG_VALUE: uncompress2:max <- -1
	#DEBUG_VALUE: uncompress2:left <- $r15
	#DEBUG_VALUE: uncompress2:err <- $ebx
	xorl	%eax, %eax
	jmp	.LBB0_4
.Lfunc_end0:
	.size	uncompress2, .Lfunc_end0-uncompress2
	.cfi_endproc
                                        # -- End function
	.globl	uncompress                      # -- Begin function uncompress
	.p2align	4, 0x90
	.type	uncompress,@function
uncompress:                             # @uncompress
.Lfunc_begin1:
	.loc	3 91 0 is_stmt 1                # ../../binutils-2.44/zlib/uncompr.c:91:0
	.cfi_startproc
# %bb.0:                                # %entry
	#DEBUG_VALUE: uncompress:dest <- $rdi
	#DEBUG_VALUE: uncompress:destLen <- $rsi
	#DEBUG_VALUE: uncompress:source <- $rdx
	#DEBUG_VALUE: uncompress:sourceLen <- $rcx
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	pushq	%r15
	pushq	%r14
	pushq	%r12
	pushq	%rbx
	subq	$16, %rsp
	.cfi_offset %rbx, -48
	.cfi_offset %r12, -40
	.cfi_offset %r14, -32
	.cfi_offset %r15, -24
	movq	%rcx, %rbx
	movq	%rdx, %r14
	movq	%rsi, %r15
	movq	%rdi, %r12
.Ltmp52:
	.loc	3 91 0 prologue_end             # ../../binutils-2.44/zlib/uncompr.c:91:0
	callq	mcount@PLT
.Ltmp53:
	#DEBUG_VALUE: uncompress:sourceLen <- $rbx
	#DEBUG_VALUE: uncompress:source <- $r14
	#DEBUG_VALUE: uncompress:destLen <- $r15
	#DEBUG_VALUE: uncompress:dest <- $r12
	.loc	3 0 0 is_stmt 0                 # ../../binutils-2.44/zlib/uncompr.c:0:0
	movq	%rbx, -40(%rbp)
.Ltmp54:
	#DEBUG_VALUE: uncompress:sourceLen <- [DW_OP_constu 40, DW_OP_minus, DW_OP_deref] $rbp
	leaq	-40(%rbp), %rcx
	.loc	3 92 12 is_stmt 1               # ../../binutils-2.44/zlib/uncompr.c:92:12
	movq	%r12, %rdi
	movq	%r15, %rsi
	movq	%r14, %rdx
	callq	uncompress2
.Ltmp55:
	.loc	3 92 5 is_stmt 0                # ../../binutils-2.44/zlib/uncompr.c:92:5
	addq	$16, %rsp
	popq	%rbx
	popq	%r12
.Ltmp56:
	#DEBUG_VALUE: uncompress:dest <- [DW_OP_LLVM_entry_value 1] $rdi
	popq	%r14
.Ltmp57:
	#DEBUG_VALUE: uncompress:source <- [DW_OP_LLVM_entry_value 1] $rdx
	popq	%r15
.Ltmp58:
	#DEBUG_VALUE: uncompress:destLen <- [DW_OP_LLVM_entry_value 1] $rsi
	popq	%rbp
	.cfi_def_cfa %rsp, 8
	retq
.Ltmp59:
.Lfunc_end1:
	.size	uncompress, .Lfunc_end1-uncompress
	.cfi_endproc
                                        # -- End function
	.type	.L.str,@object                  # @.str
	.section	.rodata.str1.1,"aMS",@progbits,1
.L.str:
	.asciz	"1.2.12"
	.size	.L.str, 7

	.section	.debug_loclists,"",@progbits
	.long	.Ldebug_list_header_end0-.Ldebug_list_header_start0 # Length
.Ldebug_list_header_start0:
	.short	5                               # Version
	.byte	8                               # Address size
	.byte	0                               # Segment selector size
	.long	12                              # Offset entry count
.Lloclists_table_base0:
	.long	.Ldebug_loc0-.Lloclists_table_base0
	.long	.Ldebug_loc1-.Lloclists_table_base0
	.long	.Ldebug_loc2-.Lloclists_table_base0
	.long	.Ldebug_loc3-.Lloclists_table_base0
	.long	.Ldebug_loc4-.Lloclists_table_base0
	.long	.Ldebug_loc5-.Lloclists_table_base0
	.long	.Ldebug_loc6-.Lloclists_table_base0
	.long	.Ldebug_loc7-.Lloclists_table_base0
	.long	.Ldebug_loc8-.Lloclists_table_base0
	.long	.Ldebug_loc9-.Lloclists_table_base0
	.long	.Ldebug_loc10-.Lloclists_table_base0
	.long	.Ldebug_loc11-.Lloclists_table_base0
.Ldebug_loc0:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin0-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp0-.Lfunc_begin0           #   ending offset
	.byte	1                               # Loc expr size
	.byte	85                              # DW_OP_reg5
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp0-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp6-.Lfunc_begin0           #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	72                              # -56
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp7-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp15-.Lfunc_begin0          #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	72                              # -56
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp15-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp16-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp16-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	72                              # -56
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc1:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin0-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp1-.Lfunc_begin0           #   ending offset
	.byte	1                               # Loc expr size
	.byte	84                              # DW_OP_reg4
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp1-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	83                              # DW_OP_reg3
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp10-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp11-.Lfunc_begin0          #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	84                              # DW_OP_reg4
	.byte	159                             # DW_OP_stack_value
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp13-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	83                              # DW_OP_reg3
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp13-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp18-.Lfunc_begin0          #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	64                              # -64
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp18-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp32-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	83                              # DW_OP_reg3
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp32-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp40-.Lfunc_begin0          #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	64                              # -64
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp40-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp41-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	82                              # DW_OP_reg2
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp41-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	64                              # -64
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc2:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin0-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp1-.Lfunc_begin0           #   ending offset
	.byte	1                               # Loc expr size
	.byte	81                              # DW_OP_reg1
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp1-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	92                              # DW_OP_reg12
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp10-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp11-.Lfunc_begin0          #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	81                              # DW_OP_reg1
	.byte	159                             # DW_OP_stack_value
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp14-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	92                              # DW_OP_reg12
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp14-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	81                              # DW_OP_reg1
	.byte	159                             # DW_OP_stack_value
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc3:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin0-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp1-.Lfunc_begin0           #   ending offset
	.byte	1                               # Loc expr size
	.byte	82                              # DW_OP_reg2
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp1-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	93                              # DW_OP_reg13
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp10-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp11-.Lfunc_begin0          #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	82                              # DW_OP_reg2
	.byte	159                             # DW_OP_stack_value
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp12-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	93                              # DW_OP_reg13
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp12-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp35-.Lfunc_begin0          #   ending offset
	.byte	3                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	184                             # -72
	.byte	127                             # 
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp35-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp37-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp37-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	3                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	184                             # -72
	.byte	127                             # 
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc4:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp1-.Lfunc_begin0           #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	3                               # Loc expr size
	.byte	48                              # DW_OP_lit0
	.byte	32                              # DW_OP_not
	.byte	159                             # DW_OP_stack_value
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc5:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp2-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	94                              # DW_OP_reg14
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp34-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	94                              # DW_OP_reg14
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc6:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp4-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp5-.Lfunc_begin0           #   ending offset
	.byte	1                               # Loc expr size
	.byte	95                              # DW_OP_reg15
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp7-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	95                              # DW_OP_reg15
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp48-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	95                              # DW_OP_reg15
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp50-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	1                               # Loc expr size
	.byte	95                              # DW_OP_reg15
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc7:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp8-.Lfunc_begin0           #   starting offset
	.uleb128 .Ltmp10-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # super-register DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp11-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp15-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # super-register DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp18-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp19-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # super-register DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp29-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp33-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	80                              # super-register DW_OP_reg0
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp33-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end0-.Lfunc_begin0      #   ending offset
	.byte	1                               # Loc expr size
	.byte	83                              # super-register DW_OP_reg3
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc8:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin1-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp53-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	85                              # DW_OP_reg5
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp53-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp56-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	92                              # DW_OP_reg12
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp56-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end1-.Lfunc_begin0      #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	85                              # DW_OP_reg5
	.byte	159                             # DW_OP_stack_value
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc9:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin1-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp53-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	84                              # DW_OP_reg4
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp53-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp58-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	95                              # DW_OP_reg15
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp58-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end1-.Lfunc_begin0      #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	84                              # DW_OP_reg4
	.byte	159                             # DW_OP_stack_value
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc10:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin1-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp53-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	81                              # DW_OP_reg1
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp53-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp57-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	94                              # DW_OP_reg14
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp57-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end1-.Lfunc_begin0      #   ending offset
	.byte	4                               # Loc expr size
	.byte	163                             # DW_OP_entry_value
	.byte	1                               # 1
	.byte	81                              # DW_OP_reg1
	.byte	159                             # DW_OP_stack_value
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_loc11:
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Lfunc_begin1-.Lfunc_begin0    #   starting offset
	.uleb128 .Ltmp53-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	82                              # DW_OP_reg2
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp53-.Lfunc_begin0          #   starting offset
	.uleb128 .Ltmp54-.Lfunc_begin0          #   ending offset
	.byte	1                               # Loc expr size
	.byte	83                              # DW_OP_reg3
	.byte	4                               # DW_LLE_offset_pair
	.uleb128 .Ltmp54-.Lfunc_begin0          #   starting offset
	.uleb128 .Lfunc_end1-.Lfunc_begin0      #   ending offset
	.byte	2                               # Loc expr size
	.byte	118                             # DW_OP_breg6
	.byte	88                              # -40
	.byte	0                               # DW_LLE_end_of_list
.Ldebug_list_header_end0:
	.section	.debug_abbrev,"",@progbits
	.byte	1                               # Abbreviation Code
	.byte	17                              # DW_TAG_compile_unit
	.byte	1                               # DW_CHILDREN_yes
	.byte	37                              # DW_AT_producer
	.byte	37                              # DW_FORM_strx1
	.byte	19                              # DW_AT_language
	.byte	5                               # DW_FORM_data2
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	114                             # DW_AT_str_offsets_base
	.byte	23                              # DW_FORM_sec_offset
	.byte	16                              # DW_AT_stmt_list
	.byte	23                              # DW_FORM_sec_offset
	.byte	27                              # DW_AT_comp_dir
	.byte	37                              # DW_FORM_strx1
	.byte	17                              # DW_AT_low_pc
	.byte	27                              # DW_FORM_addrx
	.byte	18                              # DW_AT_high_pc
	.byte	6                               # DW_FORM_data4
	.byte	115                             # DW_AT_addr_base
	.byte	23                              # DW_FORM_sec_offset
	.ascii	"\214\001"                      # DW_AT_loclists_base
	.byte	23                              # DW_FORM_sec_offset
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	2                               # Abbreviation Code
	.byte	22                              # DW_TAG_typedef
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	5                               # DW_FORM_data2
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	3                               # Abbreviation Code
	.byte	36                              # DW_TAG_base_type
	.byte	0                               # DW_CHILDREN_no
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	62                              # DW_AT_encoding
	.byte	11                              # DW_FORM_data1
	.byte	11                              # DW_AT_byte_size
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	4                               # Abbreviation Code
	.byte	15                              # DW_TAG_pointer_type
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	5                               # Abbreviation Code
	.byte	22                              # DW_TAG_typedef
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	6                               # Abbreviation Code
	.byte	21                              # DW_TAG_subroutine_type
	.byte	1                               # DW_CHILDREN_yes
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	39                              # DW_AT_prototyped
	.byte	25                              # DW_FORM_flag_present
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	7                               # Abbreviation Code
	.byte	5                               # DW_TAG_formal_parameter
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	8                               # Abbreviation Code
	.byte	15                              # DW_TAG_pointer_type
	.byte	0                               # DW_CHILDREN_no
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	9                               # Abbreviation Code
	.byte	21                              # DW_TAG_subroutine_type
	.byte	1                               # DW_CHILDREN_yes
	.byte	39                              # DW_AT_prototyped
	.byte	25                              # DW_FORM_flag_present
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	10                              # Abbreviation Code
	.byte	46                              # DW_TAG_subprogram
	.byte	1                               # DW_CHILDREN_yes
	.byte	17                              # DW_AT_low_pc
	.byte	27                              # DW_FORM_addrx
	.byte	18                              # DW_AT_high_pc
	.byte	6                               # DW_FORM_data4
	.byte	64                              # DW_AT_frame_base
	.byte	24                              # DW_FORM_exprloc
	.byte	122                             # DW_AT_call_all_calls
	.byte	25                              # DW_FORM_flag_present
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	39                              # DW_AT_prototyped
	.byte	25                              # DW_FORM_flag_present
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	63                              # DW_AT_external
	.byte	25                              # DW_FORM_flag_present
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	11                              # Abbreviation Code
	.byte	5                               # DW_TAG_formal_parameter
	.byte	0                               # DW_CHILDREN_no
	.byte	2                               # DW_AT_location
	.byte	34                              # DW_FORM_loclistx
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	12                              # Abbreviation Code
	.byte	52                              # DW_TAG_variable
	.byte	0                               # DW_CHILDREN_no
	.byte	2                               # DW_AT_location
	.byte	24                              # DW_FORM_exprloc
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	13                              # Abbreviation Code
	.byte	52                              # DW_TAG_variable
	.byte	0                               # DW_CHILDREN_no
	.byte	2                               # DW_AT_location
	.byte	34                              # DW_FORM_loclistx
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	14                              # Abbreviation Code
	.byte	72                              # DW_TAG_call_site
	.byte	1                               # DW_CHILDREN_yes
	.byte	127                             # DW_AT_call_origin
	.byte	19                              # DW_FORM_ref4
	.byte	125                             # DW_AT_call_return_pc
	.byte	27                              # DW_FORM_addrx
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	15                              # Abbreviation Code
	.byte	73                              # DW_TAG_call_site_parameter
	.byte	0                               # DW_CHILDREN_no
	.byte	2                               # DW_AT_location
	.byte	24                              # DW_FORM_exprloc
	.byte	126                             # DW_AT_call_value
	.byte	24                              # DW_FORM_exprloc
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	16                              # Abbreviation Code
	.byte	46                              # DW_TAG_subprogram
	.byte	1                               # DW_CHILDREN_yes
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	5                               # DW_FORM_data2
	.byte	39                              # DW_AT_prototyped
	.byte	25                              # DW_FORM_flag_present
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	60                              # DW_AT_declaration
	.byte	25                              # DW_FORM_flag_present
	.byte	63                              # DW_AT_external
	.byte	25                              # DW_FORM_flag_present
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	17                              # Abbreviation Code
	.byte	19                              # DW_TAG_structure_type
	.byte	1                               # DW_CHILDREN_yes
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	11                              # DW_AT_byte_size
	.byte	11                              # DW_FORM_data1
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	18                              # Abbreviation Code
	.byte	13                              # DW_TAG_member
	.byte	0                               # DW_CHILDREN_no
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	58                              # DW_AT_decl_file
	.byte	11                              # DW_FORM_data1
	.byte	59                              # DW_AT_decl_line
	.byte	11                              # DW_FORM_data1
	.byte	56                              # DW_AT_data_member_location
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	19                              # Abbreviation Code
	.byte	19                              # DW_TAG_structure_type
	.byte	0                               # DW_CHILDREN_no
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	60                              # DW_AT_declaration
	.byte	25                              # DW_FORM_flag_present
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	20                              # Abbreviation Code
	.byte	38                              # DW_TAG_const_type
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	21                              # Abbreviation Code
	.byte	1                               # DW_TAG_array_type
	.byte	1                               # DW_CHILDREN_yes
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	22                              # Abbreviation Code
	.byte	33                              # DW_TAG_subrange_type
	.byte	0                               # DW_CHILDREN_no
	.byte	73                              # DW_AT_type
	.byte	19                              # DW_FORM_ref4
	.byte	55                              # DW_AT_count
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	23                              # Abbreviation Code
	.byte	36                              # DW_TAG_base_type
	.byte	0                               # DW_CHILDREN_no
	.byte	3                               # DW_AT_name
	.byte	37                              # DW_FORM_strx1
	.byte	11                              # DW_AT_byte_size
	.byte	11                              # DW_FORM_data1
	.byte	62                              # DW_AT_encoding
	.byte	11                              # DW_FORM_data1
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	0                               # EOM(3)
	.section	.debug_info,"",@progbits
.Lcu_begin0:
	.long	.Ldebug_info_end0-.Ldebug_info_start0 # Length of Unit
.Ldebug_info_start0:
	.short	5                               # DWARF version number
	.byte	1                               # DWARF Unit Type
	.byte	8                               # Address Size (in bytes)
	.long	.debug_abbrev                   # Offset Into Abbrev. Section
	.byte	1                               # Abbrev [1] 0xc:0x2b1 DW_TAG_compile_unit
	.byte	0                               # DW_AT_producer
	.short	12                              # DW_AT_language
	.byte	1                               # DW_AT_name
	.long	.Lstr_offsets_base0             # DW_AT_str_offsets_base
	.long	.Lline_table_start0             # DW_AT_stmt_list
	.byte	2                               # DW_AT_comp_dir
	.byte	0                               # DW_AT_low_pc
	.long	.Lfunc_end1-.Lfunc_begin0       # DW_AT_high_pc
	.long	.Laddr_table_base0              # DW_AT_addr_base
	.long	.Lloclists_table_base0          # DW_AT_loclists_base
	.byte	2                               # Abbrev [2] 0x27:0x9 DW_TAG_typedef
	.long	48                              # DW_AT_type
	.byte	4                               # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	393                             # DW_AT_decl_line
	.byte	3                               # Abbrev [3] 0x30:0x4 DW_TAG_base_type
	.byte	3                               # DW_AT_name
	.byte	7                               # DW_AT_encoding
	.byte	4                               # DW_AT_byte_size
	.byte	4                               # Abbrev [4] 0x34:0x5 DW_TAG_pointer_type
	.long	57                              # DW_AT_type
	.byte	2                               # Abbrev [2] 0x39:0x9 DW_TAG_typedef
	.long	66                              # DW_AT_type
	.byte	7                               # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	400                             # DW_AT_decl_line
	.byte	2                               # Abbrev [2] 0x42:0x9 DW_TAG_typedef
	.long	75                              # DW_AT_type
	.byte	6                               # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	391                             # DW_AT_decl_line
	.byte	3                               # Abbrev [3] 0x4b:0x4 DW_TAG_base_type
	.byte	5                               # DW_AT_name
	.byte	8                               # DW_AT_encoding
	.byte	1                               # DW_AT_byte_size
	.byte	5                               # Abbrev [5] 0x4f:0x8 DW_TAG_typedef
	.long	87                              # DW_AT_type
	.byte	9                               # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.byte	81                              # DW_AT_decl_line
	.byte	4                               # Abbrev [4] 0x57:0x5 DW_TAG_pointer_type
	.long	92                              # DW_AT_type
	.byte	6                               # Abbrev [6] 0x5c:0x15 DW_TAG_subroutine_type
	.long	113                             # DW_AT_type
                                        # DW_AT_prototyped
	.byte	7                               # Abbrev [7] 0x61:0x5 DW_TAG_formal_parameter
	.long	113                             # DW_AT_type
	.byte	7                               # Abbrev [7] 0x66:0x5 DW_TAG_formal_parameter
	.long	39                              # DW_AT_type
	.byte	7                               # Abbrev [7] 0x6b:0x5 DW_TAG_formal_parameter
	.long	39                              # DW_AT_type
	.byte	0                               # End Of Children Mark
	.byte	2                               # Abbrev [2] 0x71:0x9 DW_TAG_typedef
	.long	122                             # DW_AT_type
	.byte	8                               # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	409                             # DW_AT_decl_line
	.byte	8                               # Abbrev [8] 0x7a:0x1 DW_TAG_pointer_type
	.byte	5                               # Abbrev [5] 0x7b:0x8 DW_TAG_typedef
	.long	131                             # DW_AT_type
	.byte	10                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.byte	82                              # DW_AT_decl_line
	.byte	4                               # Abbrev [4] 0x83:0x5 DW_TAG_pointer_type
	.long	136                             # DW_AT_type
	.byte	9                               # Abbrev [9] 0x88:0xc DW_TAG_subroutine_type
                                        # DW_AT_prototyped
	.byte	7                               # Abbrev [7] 0x89:0x5 DW_TAG_formal_parameter
	.long	113                             # DW_AT_type
	.byte	7                               # Abbrev [7] 0x8e:0x5 DW_TAG_formal_parameter
	.long	113                             # DW_AT_type
	.byte	0                               # End Of Children Mark
	.byte	3                               # Abbrev [3] 0x94:0x4 DW_TAG_base_type
	.byte	11                              # DW_AT_name
	.byte	5                               # DW_AT_encoding
	.byte	4                               # DW_AT_byte_size
	.byte	2                               # Abbrev [2] 0x98:0x9 DW_TAG_typedef
	.long	161                             # DW_AT_type
	.byte	13                              # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	394                             # DW_AT_decl_line
	.byte	3                               # Abbrev [3] 0xa1:0x4 DW_TAG_base_type
	.byte	12                              # DW_AT_name
	.byte	7                               # DW_AT_encoding
	.byte	8                               # DW_AT_byte_size
	.byte	10                              # Abbrev [10] 0xa5:0xa3 DW_TAG_subprogram
	.byte	0                               # DW_AT_low_pc
	.long	.Lfunc_end0-.Lfunc_begin0       # DW_AT_high_pc
	.byte	1                               # DW_AT_frame_base
	.byte	86
                                        # DW_AT_call_all_calls
	.byte	36                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	27                              # DW_AT_decl_line
                                        # DW_AT_prototyped
	.long	148                             # DW_AT_type
                                        # DW_AT_external
	.byte	11                              # Abbrev [11] 0xb4:0x9 DW_TAG_formal_parameter
	.byte	0                               # DW_AT_location
	.byte	41                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	28                              # DW_AT_decl_line
	.long	52                              # DW_AT_type
	.byte	11                              # Abbrev [11] 0xbd:0x9 DW_TAG_formal_parameter
	.byte	1                               # DW_AT_location
	.byte	42                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	29                              # DW_AT_decl_line
	.long	666                             # DW_AT_type
	.byte	11                              # Abbrev [11] 0xc6:0x9 DW_TAG_formal_parameter
	.byte	2                               # DW_AT_location
	.byte	44                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	30                              # DW_AT_decl_line
	.long	680                             # DW_AT_type
	.byte	11                              # Abbrev [11] 0xcf:0x9 DW_TAG_formal_parameter
	.byte	3                               # DW_AT_location
	.byte	45                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	31                              # DW_AT_decl_line
	.long	690                             # DW_AT_type
	.byte	12                              # Abbrev [12] 0xd8:0xc DW_TAG_variable
	.byte	3                               # DW_AT_location
	.byte	145
	.ascii	"\310~"
	.byte	38                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	33                              # DW_AT_decl_line
	.long	366                             # DW_AT_type
	.byte	12                              # Abbrev [12] 0xe4:0xb DW_TAG_variable
	.byte	2                               # DW_AT_location
	.byte	145
	.byte	87
	.byte	39                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	37                              # DW_AT_decl_line
	.long	650                             # DW_AT_type
	.byte	13                              # Abbrev [13] 0xef:0x9 DW_TAG_variable
	.byte	4                               # DW_AT_location
	.byte	46                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	35                              # DW_AT_decl_line
	.long	695                             # DW_AT_type
	.byte	13                              # Abbrev [13] 0xf8:0x9 DW_TAG_variable
	.byte	5                               # DW_AT_location
	.byte	47                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	36                              # DW_AT_decl_line
	.long	152                             # DW_AT_type
	.byte	13                              # Abbrev [13] 0x101:0x9 DW_TAG_variable
	.byte	6                               # DW_AT_location
	.byte	48                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	36                              # DW_AT_decl_line
	.long	152                             # DW_AT_type
	.byte	13                              # Abbrev [13] 0x10a:0x9 DW_TAG_variable
	.byte	7                               # DW_AT_location
	.byte	49                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	34                              # DW_AT_decl_line
	.long	148                             # DW_AT_type
	.byte	14                              # Abbrev [14] 0x113:0x14 DW_TAG_call_site
	.long	328                             # DW_AT_call_origin
	.byte	1                               # DW_AT_call_return_pc
	.byte	15                              # Abbrev [15] 0x119:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	81
	.byte	2                               # DW_AT_call_value
	.byte	16
	.byte	112
	.byte	15                              # Abbrev [15] 0x11f:0x7 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	85
	.byte	3                               # DW_AT_call_value
	.byte	145
	.ascii	"\310~"
	.byte	0                               # End Of Children Mark
	.byte	14                              # Abbrev [14] 0x127:0x12 DW_TAG_call_site
	.long	532                             # DW_AT_call_origin
	.byte	2                               # DW_AT_call_return_pc
	.byte	15                              # Abbrev [15] 0x12d:0x5 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	84
	.byte	1                               # DW_AT_call_value
	.byte	48
	.byte	15                              # Abbrev [15] 0x132:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	85
	.byte	2                               # DW_AT_call_value
	.byte	125
	.byte	0
	.byte	0                               # End Of Children Mark
	.byte	14                              # Abbrev [14] 0x139:0xe DW_TAG_call_site
	.long	552                             # DW_AT_call_origin
	.byte	3                               # DW_AT_call_return_pc
	.byte	15                              # Abbrev [15] 0x13f:0x7 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	85
	.byte	3                               # DW_AT_call_value
	.byte	145
	.ascii	"\310~"
	.byte	0                               # End Of Children Mark
	.byte	0                               # End Of Children Mark
	.byte	16                              # Abbrev [16] 0x148:0x19 DW_TAG_subprogram
	.byte	14                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.short	1783                            # DW_AT_decl_line
                                        # DW_AT_prototyped
	.long	148                             # DW_AT_type
                                        # DW_AT_declaration
                                        # DW_AT_external
	.byte	7                               # Abbrev [7] 0x151:0x5 DW_TAG_formal_parameter
	.long	353                             # DW_AT_type
	.byte	7                               # Abbrev [7] 0x156:0x5 DW_TAG_formal_parameter
	.long	522                             # DW_AT_type
	.byte	7                               # Abbrev [7] 0x15b:0x5 DW_TAG_formal_parameter
	.long	148                             # DW_AT_type
	.byte	0                               # End Of Children Mark
	.byte	5                               # Abbrev [5] 0x161:0x8 DW_TAG_typedef
	.long	361                             # DW_AT_type
	.byte	33                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.byte	108                             # DW_AT_decl_line
	.byte	4                               # Abbrev [4] 0x169:0x5 DW_TAG_pointer_type
	.long	366                             # DW_AT_type
	.byte	5                               # Abbrev [5] 0x16e:0x8 DW_TAG_typedef
	.long	374                             # DW_AT_type
	.byte	32                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.byte	106                             # DW_AT_decl_line
	.byte	17                              # Abbrev [17] 0x176:0x84 DW_TAG_structure_type
	.byte	31                              # DW_AT_name
	.byte	112                             # DW_AT_byte_size
	.byte	2                               # DW_AT_decl_file
	.byte	86                              # DW_AT_decl_line
	.byte	18                              # Abbrev [18] 0x17b:0x9 DW_TAG_member
	.byte	15                              # DW_AT_name
	.long	52                              # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	87                              # DW_AT_decl_line
	.byte	0                               # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x184:0x9 DW_TAG_member
	.byte	16                              # DW_AT_name
	.long	39                              # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	88                              # DW_AT_decl_line
	.byte	8                               # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x18d:0x9 DW_TAG_member
	.byte	17                              # DW_AT_name
	.long	152                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	89                              # DW_AT_decl_line
	.byte	16                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x196:0x9 DW_TAG_member
	.byte	18                              # DW_AT_name
	.long	52                              # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	91                              # DW_AT_decl_line
	.byte	24                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x19f:0x9 DW_TAG_member
	.byte	19                              # DW_AT_name
	.long	39                              # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	92                              # DW_AT_decl_line
	.byte	32                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1a8:0x9 DW_TAG_member
	.byte	20                              # DW_AT_name
	.long	152                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	93                              # DW_AT_decl_line
	.byte	40                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1b1:0x9 DW_TAG_member
	.byte	21                              # DW_AT_name
	.long	506                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	95                              # DW_AT_decl_line
	.byte	48                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1ba:0x9 DW_TAG_member
	.byte	23                              # DW_AT_name
	.long	515                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	96                              # DW_AT_decl_line
	.byte	56                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1c3:0x9 DW_TAG_member
	.byte	25                              # DW_AT_name
	.long	79                              # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	98                              # DW_AT_decl_line
	.byte	64                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1cc:0x9 DW_TAG_member
	.byte	26                              # DW_AT_name
	.long	123                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	99                              # DW_AT_decl_line
	.byte	72                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1d5:0x9 DW_TAG_member
	.byte	27                              # DW_AT_name
	.long	113                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	100                             # DW_AT_decl_line
	.byte	80                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1de:0x9 DW_TAG_member
	.byte	28                              # DW_AT_name
	.long	148                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	102                             # DW_AT_decl_line
	.byte	88                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1e7:0x9 DW_TAG_member
	.byte	29                              # DW_AT_name
	.long	152                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	104                             # DW_AT_decl_line
	.byte	96                              # DW_AT_data_member_location
	.byte	18                              # Abbrev [18] 0x1f0:0x9 DW_TAG_member
	.byte	30                              # DW_AT_name
	.long	152                             # DW_AT_type
	.byte	2                               # DW_AT_decl_file
	.byte	105                             # DW_AT_decl_line
	.byte	104                             # DW_AT_data_member_location
	.byte	0                               # End Of Children Mark
	.byte	4                               # Abbrev [4] 0x1fa:0x5 DW_TAG_pointer_type
	.long	511                             # DW_AT_type
	.byte	3                               # Abbrev [3] 0x1ff:0x4 DW_TAG_base_type
	.byte	22                              # DW_AT_name
	.byte	6                               # DW_AT_encoding
	.byte	1                               # DW_AT_byte_size
	.byte	4                               # Abbrev [4] 0x203:0x5 DW_TAG_pointer_type
	.long	520                             # DW_AT_type
	.byte	19                              # Abbrev [19] 0x208:0x2 DW_TAG_structure_type
	.byte	24                              # DW_AT_name
                                        # DW_AT_declaration
	.byte	4                               # Abbrev [4] 0x20a:0x5 DW_TAG_pointer_type
	.long	527                             # DW_AT_type
	.byte	20                              # Abbrev [20] 0x20f:0x5 DW_TAG_const_type
	.long	511                             # DW_AT_type
	.byte	16                              # Abbrev [16] 0x214:0x14 DW_TAG_subprogram
	.byte	34                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.short	400                             # DW_AT_decl_line
                                        # DW_AT_prototyped
	.long	148                             # DW_AT_type
                                        # DW_AT_declaration
                                        # DW_AT_external
	.byte	7                               # Abbrev [7] 0x21d:0x5 DW_TAG_formal_parameter
	.long	353                             # DW_AT_type
	.byte	7                               # Abbrev [7] 0x222:0x5 DW_TAG_formal_parameter
	.long	148                             # DW_AT_type
	.byte	0                               # End Of Children Mark
	.byte	16                              # Abbrev [16] 0x228:0xf DW_TAG_subprogram
	.byte	35                              # DW_AT_name
	.byte	2                               # DW_AT_decl_file
	.short	520                             # DW_AT_decl_line
                                        # DW_AT_prototyped
	.long	148                             # DW_AT_type
                                        # DW_AT_declaration
                                        # DW_AT_external
	.byte	7                               # Abbrev [7] 0x231:0x5 DW_TAG_formal_parameter
	.long	353                             # DW_AT_type
	.byte	0                               # End Of Children Mark
	.byte	10                              # Abbrev [10] 0x237:0x53 DW_TAG_subprogram
	.byte	4                               # DW_AT_low_pc
	.long	.Lfunc_end1-.Lfunc_begin1       # DW_AT_high_pc
	.byte	1                               # DW_AT_frame_base
	.byte	86
                                        # DW_AT_call_all_calls
	.byte	37                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	86                              # DW_AT_decl_line
                                        # DW_AT_prototyped
	.long	148                             # DW_AT_type
                                        # DW_AT_external
	.byte	11                              # Abbrev [11] 0x246:0x9 DW_TAG_formal_parameter
	.byte	8                               # DW_AT_location
	.byte	41                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	87                              # DW_AT_decl_line
	.long	52                              # DW_AT_type
	.byte	11                              # Abbrev [11] 0x24f:0x9 DW_TAG_formal_parameter
	.byte	9                               # DW_AT_location
	.byte	42                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	88                              # DW_AT_decl_line
	.long	666                             # DW_AT_type
	.byte	11                              # Abbrev [11] 0x258:0x9 DW_TAG_formal_parameter
	.byte	10                              # DW_AT_location
	.byte	44                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	89                              # DW_AT_decl_line
	.long	680                             # DW_AT_type
	.byte	11                              # Abbrev [11] 0x261:0x9 DW_TAG_formal_parameter
	.byte	11                              # DW_AT_location
	.byte	45                              # DW_AT_name
	.byte	3                               # DW_AT_decl_file
	.byte	90                              # DW_AT_decl_line
	.long	152                             # DW_AT_type
	.byte	14                              # Abbrev [14] 0x26a:0x1f DW_TAG_call_site
	.long	165                             # DW_AT_call_origin
	.byte	5                               # DW_AT_call_return_pc
	.byte	15                              # Abbrev [15] 0x270:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	81
	.byte	2                               # DW_AT_call_value
	.byte	126
	.byte	0
	.byte	15                              # Abbrev [15] 0x276:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	84
	.byte	2                               # DW_AT_call_value
	.byte	127
	.byte	0
	.byte	15                              # Abbrev [15] 0x27c:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	85
	.byte	2                               # DW_AT_call_value
	.byte	124
	.byte	0
	.byte	15                              # Abbrev [15] 0x282:0x6 DW_TAG_call_site_parameter
	.byte	1                               # DW_AT_location
	.byte	82
	.byte	2                               # DW_AT_call_value
	.byte	145
	.byte	88
	.byte	0                               # End Of Children Mark
	.byte	0                               # End Of Children Mark
	.byte	21                              # Abbrev [21] 0x28a:0xc DW_TAG_array_type
	.long	66                              # DW_AT_type
	.byte	22                              # Abbrev [22] 0x28f:0x6 DW_TAG_subrange_type
	.long	662                             # DW_AT_type
	.byte	1                               # DW_AT_count
	.byte	0                               # End Of Children Mark
	.byte	23                              # Abbrev [23] 0x296:0x4 DW_TAG_base_type
	.byte	40                              # DW_AT_name
	.byte	8                               # DW_AT_byte_size
	.byte	7                               # DW_AT_encoding
	.byte	4                               # Abbrev [4] 0x29a:0x5 DW_TAG_pointer_type
	.long	671                             # DW_AT_type
	.byte	2                               # Abbrev [2] 0x29f:0x9 DW_TAG_typedef
	.long	152                             # DW_AT_type
	.byte	43                              # DW_AT_name
	.byte	1                               # DW_AT_decl_file
	.short	405                             # DW_AT_decl_line
	.byte	4                               # Abbrev [4] 0x2a8:0x5 DW_TAG_pointer_type
	.long	685                             # DW_AT_type
	.byte	20                              # Abbrev [20] 0x2ad:0x5 DW_TAG_const_type
	.long	57                              # DW_AT_type
	.byte	4                               # Abbrev [4] 0x2b2:0x5 DW_TAG_pointer_type
	.long	152                             # DW_AT_type
	.byte	20                              # Abbrev [20] 0x2b7:0x5 DW_TAG_const_type
	.long	39                              # DW_AT_type
	.byte	0                               # End Of Children Mark
.Ldebug_info_end0:
	.section	.debug_str_offsets,"",@progbits
	.long	204                             # Length of String Offsets Set
	.short	5
	.short	0
.Lstr_offsets_base0:
	.section	.debug_str,"MS",@progbits,1
.Linfo_string0:
	.asciz	"clang version 14.0.6"          # string offset=0
.Linfo_string1:
	.asciz	"uncompr.c"                     # string offset=21
.Linfo_string2:
	.asciz	"/home/awen/git/DSGFuzz/benchmarks/binutils/build/zlib" # string offset=31
.Linfo_string3:
	.asciz	"unsigned int"                  # string offset=85
.Linfo_string4:
	.asciz	"uInt"                          # string offset=98
.Linfo_string5:
	.asciz	"unsigned char"                 # string offset=103
.Linfo_string6:
	.asciz	"Byte"                          # string offset=117
.Linfo_string7:
	.asciz	"Bytef"                         # string offset=122
.Linfo_string8:
	.asciz	"voidpf"                        # string offset=128
.Linfo_string9:
	.asciz	"alloc_func"                    # string offset=135
.Linfo_string10:
	.asciz	"free_func"                     # string offset=146
.Linfo_string11:
	.asciz	"int"                           # string offset=156
.Linfo_string12:
	.asciz	"unsigned long"                 # string offset=160
.Linfo_string13:
	.asciz	"uLong"                         # string offset=174
.Linfo_string14:
	.asciz	"inflateInit_"                  # string offset=180
.Linfo_string15:
	.asciz	"next_in"                       # string offset=193
.Linfo_string16:
	.asciz	"avail_in"                      # string offset=201
.Linfo_string17:
	.asciz	"total_in"                      # string offset=210
.Linfo_string18:
	.asciz	"next_out"                      # string offset=219
.Linfo_string19:
	.asciz	"avail_out"                     # string offset=228
.Linfo_string20:
	.asciz	"total_out"                     # string offset=238
.Linfo_string21:
	.asciz	"msg"                           # string offset=248
.Linfo_string22:
	.asciz	"char"                          # string offset=252
.Linfo_string23:
	.asciz	"state"                         # string offset=257
.Linfo_string24:
	.asciz	"internal_state"                # string offset=263
.Linfo_string25:
	.asciz	"zalloc"                        # string offset=278
.Linfo_string26:
	.asciz	"zfree"                         # string offset=285
.Linfo_string27:
	.asciz	"opaque"                        # string offset=291
.Linfo_string28:
	.asciz	"data_type"                     # string offset=298
.Linfo_string29:
	.asciz	"adler"                         # string offset=308
.Linfo_string30:
	.asciz	"reserved"                      # string offset=314
.Linfo_string31:
	.asciz	"z_stream_s"                    # string offset=323
.Linfo_string32:
	.asciz	"z_stream"                      # string offset=334
.Linfo_string33:
	.asciz	"z_streamp"                     # string offset=343
.Linfo_string34:
	.asciz	"inflate"                       # string offset=353
.Linfo_string35:
	.asciz	"inflateEnd"                    # string offset=361
.Linfo_string36:
	.asciz	"uncompress2"                   # string offset=372
.Linfo_string37:
	.asciz	"uncompress"                    # string offset=384
.Linfo_string38:
	.asciz	"stream"                        # string offset=395
.Linfo_string39:
	.asciz	"buf"                           # string offset=402
.Linfo_string40:
	.asciz	"__ARRAY_SIZE_TYPE__"           # string offset=406
.Linfo_string41:
	.asciz	"dest"                          # string offset=426
.Linfo_string42:
	.asciz	"destLen"                       # string offset=431
.Linfo_string43:
	.asciz	"uLongf"                        # string offset=439
.Linfo_string44:
	.asciz	"source"                        # string offset=446
.Linfo_string45:
	.asciz	"sourceLen"                     # string offset=453
.Linfo_string46:
	.asciz	"max"                           # string offset=463
.Linfo_string47:
	.asciz	"len"                           # string offset=467
.Linfo_string48:
	.asciz	"left"                          # string offset=471
.Linfo_string49:
	.asciz	"err"                           # string offset=476
	.section	.debug_str_offsets,"",@progbits
	.long	.Linfo_string0
	.long	.Linfo_string1
	.long	.Linfo_string2
	.long	.Linfo_string3
	.long	.Linfo_string4
	.long	.Linfo_string5
	.long	.Linfo_string6
	.long	.Linfo_string7
	.long	.Linfo_string8
	.long	.Linfo_string9
	.long	.Linfo_string10
	.long	.Linfo_string11
	.long	.Linfo_string12
	.long	.Linfo_string13
	.long	.Linfo_string14
	.long	.Linfo_string15
	.long	.Linfo_string16
	.long	.Linfo_string17
	.long	.Linfo_string18
	.long	.Linfo_string19
	.long	.Linfo_string20
	.long	.Linfo_string21
	.long	.Linfo_string22
	.long	.Linfo_string23
	.long	.Linfo_string24
	.long	.Linfo_string25
	.long	.Linfo_string26
	.long	.Linfo_string27
	.long	.Linfo_string28
	.long	.Linfo_string29
	.long	.Linfo_string30
	.long	.Linfo_string31
	.long	.Linfo_string32
	.long	.Linfo_string33
	.long	.Linfo_string34
	.long	.Linfo_string35
	.long	.Linfo_string36
	.long	.Linfo_string37
	.long	.Linfo_string38
	.long	.Linfo_string39
	.long	.Linfo_string40
	.long	.Linfo_string41
	.long	.Linfo_string42
	.long	.Linfo_string43
	.long	.Linfo_string44
	.long	.Linfo_string45
	.long	.Linfo_string46
	.long	.Linfo_string47
	.long	.Linfo_string48
	.long	.Linfo_string49
	.section	.debug_addr,"",@progbits
	.long	.Ldebug_addr_end0-.Ldebug_addr_start0 # Length of contribution
.Ldebug_addr_start0:
	.short	5                               # DWARF version number
	.byte	8                               # Address size
	.byte	0                               # Segment selector size
.Laddr_table_base0:
	.quad	.Lfunc_begin0
	.quad	.Ltmp8
	.quad	.Ltmp29
	.quad	.Ltmp44
	.quad	.Lfunc_begin1
	.quad	.Ltmp55
.Ldebug_addr_end0:
	.ident	"clang version 14.0.6"
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.addrsig_sym mcount
	.section	.debug_line,"",@progbits
.Lline_table_start0:
