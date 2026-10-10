# AnyPS5 blocker map

> Generated data, community prototype, not official. Built 2026-10-10T18:44:31Z from public GitHub data of [boykopovar/AnyPS5](https://github.com/boykopovar/AnyPS5) at `29380369` plus `data/blockers.json`.

Issues read: 284 · PRs read: 2597 · titles: 154 · open blockers: 65 (57 block at least one title) · curated blockers: 15

Score = 3 × one_fix_away + 2 × frontier + total. Frontier: titles for which the blocker is the first open one. One fix away: titles for which it is the only open one.

## Focus areas

1. **libkernel** (score 90): 10 blockers on 18 titles, first stop for 15; open fix PRs 5. Top: [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106), [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482), [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872), [#2701](https://github.com/boykopovar/AnyPS5/issues/2701)
2. **Shader recompiler** (score 73): 13 blockers on 17 titles, first stop for 13; open fix PRs 8. Top: [#2548](https://github.com/boykopovar/AnyPS5/issues/2548), [#1413](https://github.com/boykopovar/AnyPS5/issues/1413), [#2871](https://github.com/boykopovar/AnyPS5/issues/2871), [#2621](https://github.com/boykopovar/AnyPS5/issues/2621)
3. **AGC driver** (score 36): 10 blockers on 11 titles, first stop for 7; open fix PRs 3. Top: [#1409](https://github.com/boykopovar/AnyPS5/issues/1409), [#2102](https://github.com/boykopovar/AnyPS5/issues/2102), [#2523](https://github.com/boykopovar/AnyPS5/issues/2523), [#479](https://github.com/boykopovar/AnyPS5/issues/479)
4. **HLE libraries** (score 25): 5 blockers on 5 titles, first stop for 4; open fix PRs 1. Top: [#2776](https://github.com/boykopovar/AnyPS5/issues/2776), [#2686](https://github.com/boykopovar/AnyPS5/issues/2686), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382)
5. **libc** (score 12): 2 blockers on 2 titles, first stop for 2; open fix PRs 1. Top: [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6091750552)

## Blocker ranking

| # | Blocker | Frontier | One fix away | Total | Score | Area | PRs | Last activity |
|--:|---|--:|--:|--:|--:|---|---|---|
| 1 | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) Packed pixel ancillary word read whole after its VGPR is reused (curated) | 6 | 5 | 6 | **33** | Shader recompiler | [AlxcBTW#25](https://github.com/AlxcBTW/AnyPS5/pull/25) open, [#2589](https://github.com/boykopovar/AnyPS5/pull/2589) open, [#2872](https://github.com/boykopovar/AnyPS5/pull/2872) merged, [#2843](https://github.com/boykopovar/AnyPS5/pull/2843) merged | 2026-10-10 |
| 2 | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) pthread_sigmask is not exported (libkernel) (curated) | 5 | 5 | 6 | **31** | libkernel | [#2106](https://github.com/boykopovar/AnyPS5/pull/2106) closed | 2026-10-10 |
| 3 | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) _umtx_op wait and wake are not implemented (curated) | 3 | 2 | 4 | **16** | libkernel | [#1482](https://github.com/boykopovar/AnyPS5/pull/1482) open | 2026-10-10 |
| 4 | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) Storage image access to a depth/stencil surface (curated) | 2 | 2 | 3 | **13** | AGC driver | [#454](https://github.com/boykopovar/AnyPS5/pull/454) open, [#2519](https://github.com/boykopovar/AnyPS5/pull/2519) closed, [#1495](https://github.com/boykopovar/AnyPS5/pull/1495) merged, [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open | 2026-10-10 |
| 5 | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) pthread_set_name_np is not exported (libkernel) (curated) | 2 | 2 | 3 | **13** | libkernel | [#1872](https://github.com/boykopovar/AnyPS5/pull/1872) closed | 2026-10-10 |
| 6 | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) Layered rendering: color views of several array slices (curated) | 3 | 0 | 4 | **10** | AGC driver | [#425](https://github.com/boykopovar/AnyPS5/pull/425) open, [#2219](https://github.com/boykopovar/AnyPS5/pull/2219) merged, [#1928](https://github.com/boykopovar/AnyPS5/pull/1928) merged, [#2695](https://github.com/boykopovar/AnyPS5/pull/2695) closed | 2026-10-10 |
| 7 | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) v_interp_mov P10/P20 of a flat input without pass-through (curated) | 3 | 0 | 3 | **9** | Shader recompiler | [AlxcBTW#12](https://github.com/AlxcBTW/AnyPS5/pull/12) open, [#2626](https://github.com/boykopovar/AnyPS5/pull/2626) merged, [#1412](https://github.com/boykopovar/AnyPS5/pull/1412) merged, [AlxcBTW#11](https://github.com/AlxcBTW/AnyPS5/pull/11) closed | 2026-10-10 |
| 8 | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) Dying Light 2 (PPSA02262) on Windows: what stops it between conversion and its own startup (mined) | 2 | 1 | 2 | **9** | — | [#2129](https://github.com/boykopovar/AnyPS5/pull/2129) merged, [#1830](https://github.com/boykopovar/AnyPS5/pull/1830) merged, [#1803](https://github.com/boykopovar/AnyPS5/pull/1803) merged | 2026-10-10 |
| 9 | [#2871](https://github.com/boykopovar/AnyPS5/issues/2871) Astro Bot (PPSA21564) on Linux/NVIDIA: NGG passthrough vertex program with s_barrier fails SPIR-V validation at its first draw on main de5e541d (mined) | 1 | 1 | 2 | **7** | Shader recompiler | [#2937](https://github.com/boykopovar/AnyPS5/pull/2937) open, [#2936](https://github.com/boykopovar/AnyPS5/pull/2936) open | 2026-10-10 |
| 10 | [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) libkernel: support kern.sdk_version in sysctlbyname (Capy Mobile PPSA92280) (mined) | 1 | 1 | 2 | **7** | libkernel | none | 2026-10-10 |
| 11 | [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) Ratchet & Clank: Rift Apart: a registered pixel shader is drawn with DB_SHADER_CONTROL=0 while its header sets 0x20601 (mined) | 1 | 1 | 2 | **7** | Shader recompiler | [#757](https://github.com/boykopovar/AnyPS5/pull/757) open | 2026-10-10 |
| 12 | [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) ProsperoStore (PPSA99000): startup stop on unresolved sceKernelGetSystemSwVersion (mined) | 1 | 1 | 1 | **6** | libkernel | none | 2026-10-10 |
| 13 | [#2886](https://github.com/boykopovar/AnyPS5/issues/2886) libkernel: Windows lstat misreports symbolic links instead of throwing (mined) | 1 | 1 | 1 | **6** | libkernel | [#2898](https://github.com/boykopovar/AnyPS5/pull/2898) open | 2026-10-10 |
| 14 | [#2809](https://github.com/boykopovar/AnyPS5/issues/2809) HFW loading: fixed host-import budget forces a multi-GiB heap mirror and OOM (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-10 |
| 15 | [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) Resident Evil 4 (PPSA07411): start-up needs a library named Party.prx; with the missing exports added it stops at sce::Json::InitParameter2::setSpecialFloatFormatType (mined) | 1 | 1 | 1 | **6** | HLE libraries | none | 2026-10-10 |
| 16 | [#2724](https://github.com/boykopovar/AnyPS5/issues/2724) Hades (PPSA03355) on Windows: start-up faults in the title's own libc.prx before any file is opened (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-10 |
| 17 | [#2689](https://github.com/boykopovar/AnyPS5/issues/2689) libkernel: export pthread_mutexattr_setprioceiling / getprioceiling (ZLvf6lVAc4M) (mined) | 1 | 1 | 1 | **6** | libkernel | [#2899](https://github.com/boykopovar/AnyPS5/pull/2899) open | 2026-10-10 |
| 18 | [#2686](https://github.com/boykopovar/AnyPS5/issues/2686) Cult of the Lamb (PPSA06465): start-up stops on unresolved import pXJh3aVk8Ks (sceContentDeleteById) (mined) | 1 | 1 | 1 | **6** | HLE libraries | none | 2026-10-10 |
| 19 | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) Road of Death (PPSA07286) fails on startup: missing libSceXml.prx (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-10 |
| 20 | [#2552](https://github.com/boykopovar/AnyPS5/issues/2552) Demon's Souls crashes 14 s after launch with a guest null read when built with ANYPS5_ENABLE_SPIRV_TOOLS=OFF (the default) (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-10 |
| 21 | [#1973](https://github.com/boykopovar/AnyPS5/issues/1973) Demons Souls v1.04 PPSA01342 Segfault upon running linked elf (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-09 |
| 22 | [#1930](https://github.com/boykopovar/AnyPS5/issues/1930) Linux: PPSA28997 (Sons of Sparta) aborts at start-up with "RTLD application heap: cannot replace an active allocator" (#693 regressed after #1515) (mined) | 1 | 1 | 1 | **6** | — | none | 2026-10-09 |
| 23 | [#1497](https://github.com/boykopovar/AnyPS5/issues/1497) Linux: a bundled libc.prx loader shim (ps5-native-app-boilerplate) binds libc imports to placeholder exports; DOOM PPSA99666 finds no WAD (mined) | 1 | 1 | 1 | **6** | Relinker | [#1529](https://github.com/boykopovar/AnyPS5/pull/1529) open, [#2332](https://github.com/boykopovar/AnyPS5/pull/2332) open, [#1307](https://github.com/boykopovar/AnyPS5/pull/1307) open, [#690](https://github.com/boykopovar/AnyPS5/pull/690) open | 2026-10-10 |
| 24 | [#1455](https://github.com/boykopovar/AnyPS5/issues/1455) Startup crash: display interface built with a null backend pointer (mined) | 1 | 1 | 1 | **6** | — | [#1630](https://github.com/boykopovar/AnyPS5/pull/1630) closed | 2026-10-09 |
| 25 | [#1034](https://github.com/boykopovar/AnyPS5/issues/1034) Balatro PPSA21402 on Windows: the title overwrites its own register lists when more than 2 flips are pending (VIDEO_OUT_FLIP_QUEUE_CAPACITY is 16) (mined) | 1 | 1 | 1 | **6** | — | [#1597](https://github.com/boykopovar/AnyPS5/pull/1597) merged, [#1100](https://github.com/boykopovar/AnyPS5/pull/1100) merged, [#1038](https://github.com/boykopovar/AnyPS5/pull/1038) merged | 2026-10-10 |
| 26 | [#1033](https://github.com/boykopovar/AnyPS5/issues/1033) Marvels Wolverine PPSA03671 Relies on consoles .prxs (mined) | 1 | 1 | 1 | **6** | — | [#1461](https://github.com/boykopovar/AnyPS5/pull/1461) merged, [#1317](https://github.com/boykopovar/AnyPS5/pull/1317) merged, [#2390](https://github.com/boykopovar/AnyPS5/pull/2390) closed | 2026-10-10 |
| 27 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) Module libSceOpusDec.prx is missing (mined) | 1 | 1 | 1 | **6** | HLE libraries | none | 2026-10-08 |
| 28 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) gethostname (-nvxBWa0iDs) is not exported (mined) | 1 | 1 | 1 | **6** | libc | [#2019](https://github.com/boykopovar/AnyPS5/pull/2019) closed, [#1975](https://github.com/boykopovar/AnyPS5/pull/1975) closed, [#1594](https://github.com/boykopovar/AnyPS5/pull/1594) closed | 2026-10-10 |
| 29 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6091750552) atoll (fLcU5G6Qrjs) is not exported (mined) | 1 | 1 | 1 | **6** | libc | [#2932](https://github.com/boykopovar/AnyPS5/pull/2932) open, [#2186](https://github.com/boykopovar/AnyPS5/pull/2186) closed, [#1852](https://github.com/boykopovar/AnyPS5/pull/1852) closed, [#1591](https://github.com/boykopovar/AnyPS5/pull/1591) closed | 2026-10-10 |
| 30 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) arc4random_buf (n1KOc0lTUEs) is not exported (mined) | 1 | 1 | 1 | **6** | HLE libraries | [#2865](https://github.com/boykopovar/AnyPS5/pull/2865) open, [#1637](https://github.com/boykopovar/AnyPS5/pull/1637) closed | 2026-10-10 |
| 31 | [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) 007 First Light (PPSA11386) on Linux: start-up stops in order and the PRs that pass them (mined) | 1 | 0 | 2 | **4** | AGC driver | [#2813](https://github.com/boykopovar/AnyPS5/pull/2813) open, [#2589](https://github.com/boykopovar/AnyPS5/pull/2589) open, [#1961](https://github.com/boykopovar/AnyPS5/pull/1961) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open | 2026-10-10 |
| 32 | [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) NVIDIA: wave64 NGG culling program reads lane 63 (curated) | 1 | 0 | 1 | **3** | Shader recompiler | [#1825](https://github.com/boykopovar/AnyPS5/pull/1825) open, [AlxcBTW#25](https://github.com/AlxcBTW/AnyPS5/pull/25) open | 2026-10-10 |
| 33 | [PR #2471](https://github.com/boykopovar/AnyPS5/pull/2471) Structurizer: selections joined at a shared loop exit (curated) | 1 | 0 | 1 | **3** | Shader recompiler | [#2471](https://github.com/boykopovar/AnyPS5/pull/2471) draft | 2026-10-10 |
| 34 | [siglongjmp](https://github.com/boykopovar/AnyPS5/issues/1578) siglongjmp is not exported (libkernel) (curated) | 1 | 0 | 1 | **3** | libkernel | none | — |
| 35 | [#2476](https://github.com/boykopovar/AnyPS5/issues/2476) Windows: Astro's Playroom (PPSA01325) fails to load libSceJobManager.prx (error 126) (mined) | 1 | 0 | 1 | **3** | — | [#2924](https://github.com/boykopovar/AnyPS5/pull/2924) closed | 2026-10-10 |
| 36 | [#1920](https://github.com/boykopovar/AnyPS5/issues/1920) Ghost of Yōtei (PPSA26344): unsupported scalar source operand code 235 at program counter 856 (mined) | 1 | 0 | 1 | **3** | Shader recompiler | [#1940](https://github.com/boykopovar/AnyPS5/pull/1940) open, [#1837](https://github.com/boykopovar/AnyPS5/pull/1837) merged, [#2700](https://github.com/boykopovar/AnyPS5/pull/2700) closed | 2026-10-10 |
| 37 | [#479](https://github.com/boykopovar/AnyPS5/issues/479) AGC: SRT walker statically evaluates a scalar load behind a per-lane exec guard and fails on a NULL pointer (mined) | 1 | 0 | 1 | **3** | AGC driver | [#290](https://github.com/boykopovar/AnyPS5/pull/290) open, [#759](https://github.com/boykopovar/AnyPS5/pull/759) merged, [#285](https://github.com/boykopovar/AnyPS5/pull/285) merged, [#283](https://github.com/boykopovar/AnyPS5/pull/283) merged | 2026-10-10 |
| 38 | [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) v_fma_mix* in FLOAT_MODE 0xcc (f16 round toward zero) (curated) | 0 | 0 | 2 | **2** | Shader recompiler | [AlxcBTW#19](https://github.com/AlxcBTW/AnyPS5/pull/19) open, [AlxcBTW#23](https://github.com/AlxcBTW/AnyPS5/pull/23) open, [AlxcBTW#17](https://github.com/AlxcBTW/AnyPS5/pull/17) closed | 2026-10-10 |
| 39 | [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) Recompiler: f32 product tininess is checked before rounding (RDNA2 checks after), and the check makes float-heavy shaders slow to compile (mined) | 0 | 0 | 2 | **2** | Shader recompiler | none | 2026-10-10 |
| 40 | [#2642](https://github.com/boykopovar/AnyPS5/issues/2642) Structurizer: shared merge splitting never terminates in a two-latch loop (curated) | 0 | 0 | 1 | **1** | Shader recompiler | [AlxcBTW#20](https://github.com/AlxcBTW/AnyPS5/pull/20) open, [AlxcBTW#24](https://github.com/AlxcBTW/AnyPS5/pull/24) open, [#2471](https://github.com/boykopovar/AnyPS5/pull/2471) draft | 2026-10-10 |
| 41 | [PR #2054](https://github.com/boykopovar/AnyPS5/pull/2054) Windows: direct memory mapped one 16 KiB view at a time (curated) | 0 | 0 | 1 | **1** | libkernel | [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open | 2026-10-10 |
| 42 | [PR #425](https://github.com/boykopovar/AnyPS5/pull/425) Depth surface sampled as a cube texture (curated) | 0 | 0 | 1 | **1** | AGC driver | [#425](https://github.com/boykopovar/AnyPS5/pull/425) open | 2026-10-10 |
| 43 | [#2914](https://github.com/boykopovar/AnyPS5/issues/2914) Astro's Playroom (PPSA01325): shader ABI resolution passes a different Shader* header pointer for the same code (mined) | 0 | 0 | 1 | **1** | AGC driver | none | 2026-10-10 |
| 44 | [#2811](https://github.com/boykopovar/AnyPS5/issues/2811) libSceNet Sockets implementation issue (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-10 |
| 45 | [#2775](https://github.com/boykopovar/AnyPS5/issues/2775) Astro Bot: GPU hang (ring timeout) in a mesh-shader draw of 0x50000ab00, 40 workgroups, on RADV/RDNA4 (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-10 |
| 46 | [#2774](https://github.com/boykopovar/AnyPS5/issues/2774) Recompiler: MemoryIndexBelongsTo walks the whole program on every call; about half of a warm start-up's CPU on 007 First Light (mined) | 0 | 0 | 1 | **1** | Shader recompiler | [#2813](https://github.com/boykopovar/AnyPS5/pull/2813) open, [SleglJan#23](https://github.com/SleglJan/AnyPS5/pull/23) open | 2026-10-10 |
| 47 | [#2747](https://github.com/boykopovar/AnyPS5/issues/2747) Shader recompile fails on v_cvt_f16_u16 SDWA with a byte source select (Silent Hill: Townfall) (mined) | 0 | 0 | 1 | **1** | Shader recompiler | [#2838](https://github.com/boykopovar/AnyPS5/pull/2838) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open | 2026-10-10 |
| 48 | [#2715](https://github.com/boykopovar/AnyPS5/issues/2715) Ghost of Yōtei: compute shader 0x80003aa700 loads its T# from a buffer at an index read from another buffer in a loop (GetImageResource dword 0 is not a valid runtime value) (mined) | 0 | 0 | 1 | **1** | Shader recompiler | none | 2026-10-10 |
| 49 | [#2712](https://github.com/boykopovar/AnyPS5/issues/2712) Astro Bot: a 2D-array comparison sample with emulated compare has no prepared mode for a plain 2D T# (image descriptor is incompatible with the static runtime image interface) (mined) | 0 | 0 | 1 | **1** | AGC driver | [#2936](https://github.com/boykopovar/AnyPS5/pull/2936) open, [#2146](https://github.com/boykopovar/AnyPS5/pull/2146) open | 2026-10-10 |
| 50 | [#2687](https://github.com/boykopovar/AnyPS5/issues/2687) libkernel: non-fixed map hints inside a sceKernelReserveVirtualRange range are placed elsewhere (mined) | 0 | 0 | 1 | **1** | libkernel | [#2907](https://github.com/boykopovar/AnyPS5/pull/2907) open | 2026-10-10 |
| 51 | [#2648](https://github.com/boykopovar/AnyPS5/issues/2648) Palworld (PPSA23126): next start-up stop is unresolved import oiOi7vgPfAY (sceAudioOut2EnableChat) (mined) | 0 | 0 | 1 | **1** | HLE libraries | [#2659](https://github.com/boykopovar/AnyPS5/pull/2659) closed | 2026-10-10 |
| 52 | [#2366](https://github.com/boykopovar/AnyPS5/issues/2366) Sampling a D16 depth surface's memory as a half-width 32-bit texture (PPSA15657): "sampling the depth plane ... is not implemented" (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-09 |
| 53 | [#2365](https://github.com/boykopovar/AnyPS5/issues/2365) UE4 title (PPSA15657): LowLevelFatalError "RemoveFromOuterMap NumRemoved = 0" when the title screen opens the menu (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-10 |
| 54 | [#2355](https://github.com/boykopovar/AnyPS5/issues/2355) TechnicalDebt evidence: PPSA26344 call sites for X+4jdIS75P0 and dbOlWdppb4o (unknown function info) (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-09 |
| 55 | [#1970](https://github.com/boykopovar/AnyPS5/issues/1970) agc-driver: write-back drops GPU results of full 64 KiB blocks of 1920x1080 render targets (PPSA12544 backgrounds garbled) (mined) | 0 | 0 | 1 | **1** | AGC driver | [#1997](https://github.com/boykopovar/AnyPS5/pull/1997) closed, [#2791](https://github.com/boykopovar/AnyPS5/pull/2791) open, [#1995](https://github.com/boykopovar/AnyPS5/pull/1995) merged, [#1969](https://github.com/boykopovar/AnyPS5/pull/1969) merged | 2026-10-10 |
| 56 | [#865](https://github.com/boykopovar/AnyPS5/issues/865) agc-driver: storage image write-back drops GPU results for CPU-stamped 64 KiB edge blocks (boxes in Silksong's menu text) (mined) | 0 | 0 | 1 | **1** | AGC driver | [#1599](https://github.com/boykopovar/AnyPS5/pull/1599) merged, [#1918](https://github.com/boykopovar/AnyPS5/pull/1918) closed | 2026-10-10 |
| 57 | [#665](https://github.com/boykopovar/AnyPS5/issues/665) AGC sampler: border colour table (BORDER_COLOR_TYPE 3) not implemented (mined) | 0 | 0 | 1 | **1** | AGC driver | [#1221](https://github.com/boykopovar/AnyPS5/pull/1221) closed, [#941](https://github.com/boykopovar/AnyPS5/pull/941) merged, [#668](https://github.com/boykopovar/AnyPS5/pull/668) merged, [#2392](https://github.com/boykopovar/AnyPS5/pull/2392) closed | 2026-10-10 |

## Titles

| ID | Title | Best stage | Where | Open blockers, in order |
|---|---|---|---|---|
| `PPSA02929` | Dreaming Sarah | Playable (upstream) | Windows · main | — |
| `PPSA16064` | Minecraft Dungeons II | Playable (curated) | main + open PRs | [#2811](https://github.com/boykopovar/AnyPS5/issues/2811) |
| `PPSA04263` | Grand Theft Auto V | Ingame (mined) | PR #153 | — |
| `PPSA04264` | GTA V | Ingame (mined) | Windows · NVIDIA · PR #494 | — |
| `PPSA36082` | Hades II | Ingame (mined) | Linux · NVIDIA · PR #2169 | — |
| `PPSA05684` | Uncharted: Legacy of Thieves Collection | Ingame (mined) | Linux · NVIDIA · PR #2915 | — |
| `PPSA21564` | Astro Bot | Ingame (mined) | Linux · NVIDIA · PR #305 | [#2871](https://github.com/boykopovar/AnyPS5/issues/2871) |
| `PPSA01341` | Demon's Souls | Ingame (mined) | Linux · NVIDIA · PR #1924 | [#2552](https://github.com/boykopovar/AnyPS5/issues/2552) |
| `PPSA28997` | God of War: Sons of Sparta | Ingame (mined) | Linux · NVIDIA · PR #1479 | [#1930](https://github.com/boykopovar/AnyPS5/issues/1930) |
| `PPSA14632` | LEGO Horizon Adventures | Ingame (mined) | Linux · AMD · PR #2792 | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA15657` | Disney Epic Mickey: Rebrushed | Ingame (mined) | Windows · AMD · PR #2481 | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2365](https://github.com/boykopovar/AnyPS5/issues/2365) → [#2366](https://github.com/boykopovar/AnyPS5/issues/2366) |
| `PPSA26344` | Ghost of Yōtei | Ingame (mined) | Windows · NVIDIA · PR #1267 | [#1920](https://github.com/boykopovar/AnyPS5/issues/1920) → [#2355](https://github.com/boykopovar/AnyPS5/issues/2355) → [#2715](https://github.com/boykopovar/AnyPS5/issues/2715) |
| `PPSA12544` | Hollow Knight: Silksong | Ingame (mined) | Windows · NVIDIA · main | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) → [#865](https://github.com/boykopovar/AnyPS5/issues/865) → [#1970](https://github.com/boykopovar/AnyPS5/issues/1970) |
| `PPSA21567` | Astro Bot | Ingame (mined) | Linux · AMD · PR #1584 | [#479](https://github.com/boykopovar/AnyPS5/issues/479) → [#665](https://github.com/boykopovar/AnyPS5/issues/665) → [#2712](https://github.com/boykopovar/AnyPS5/issues/2712) → [#2775](https://github.com/boykopovar/AnyPS5/issues/2775) → [#2871](https://github.com/boykopovar/AnyPS5/issues/2871) |
| `PPSA29141` | Adds LEGO Party! | Menus (mined) | Windows · NVIDIA · PR #2055 | — |
| `PPSA22520` | Seen | Menus (mined) | Windows · PR #964 | — |
| `PPSA05324` | Sonic Origins | Menus (mined) | Windows · NVIDIA · PR #849 | — |
| `PPSA21402` | Balatro | Menus (mined) | Linux · NVIDIA · PR #1197 | [#1034](https://github.com/boykopovar/AnyPS5/issues/1034) |
| `PPSA01342` | Demon's Souls | Menus (mined) | Windows · NVIDIA · main | [#1973](https://github.com/boykopovar/AnyPS5/issues/1973) |
| `PPSA99920` | Prospero Vibrate | Menus (curated) | Windows · NVIDIA · main + #2821, #2106 and AlxcBTW#21 | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA01325` | Astro's Playroom | Menus (mined) | Windows · NVIDIA · PR #2156 | [#2476](https://github.com/boykopovar/AnyPS5/issues/2476) → [#2914](https://github.com/boykopovar/AnyPS5/issues/2914) |
| `PPSA99050` | Homebrew UI Lab | Menus (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) |
| `PPSA39410` | VITA5 | Menus (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) |
| `PPSA98001` | PokeMMO | Menus (curated) | Windows · NVIDIA · main + #1482, #2106, #1872, siglongjmp and AlxcBTW#19 | [siglongjmp](https://github.com/boykopovar/AnyPS5/issues/1578) → [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) → [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) → [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) → [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) |
| `PPSA09706` | Persona 5 Tactica | Presents (mined) | Windows · PR #1222 | — |
| `PPSA01736` | Planet Coaster | Presents (mined) | Windows · NVIDIA · PR #2152 | — |
| `PPSA07906` |  | Presents (mined) | Windows · NVIDIA · PR #1709 | — |
| `PPSA59322` |  | Presents (mined) | Linux · AMD · PR #1915 | — |
| `PPSA99006` | ProsperoPuzzles | Presents (mined) | Windows · NVIDIA · main | — |
| `PPSA01289` | Sackboy: A Big Adventure | Presents (mined) | Windows · PR #2075 | — |
| `PPSA28416` | STAR WARS: Galactic Racer | Presents (mined) | Windows · PR #2888 | — |
| `PPSA23566` | UFC 6 | Presents (mined) | Windows · NVIDIA · PR #1235 | — |
| `PPSA29413` | Wobbly Life | Presents (mined) | Windows · NVIDIA · PR #2212 | — |
| `PPSA99666` | DOOM | Presents (mined) | Windows · NVIDIA · PR #1688 | [#1497](https://github.com/boykopovar/AnyPS5/issues/1497) |
| `PPSA03671` | Marvel's Wolverine | Presents (mined) | Windows · NVIDIA · PR #197 | [#1033](https://github.com/boykopovar/AnyPS5/issues/1033) |
| `PPSA02100` | Stray | Presents (curated) | Windows · NVIDIA · main | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA30279` | Taxi Chaos 2 | Presents (curated) | Windows · NVIDIA · main + local patches | [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) (Windows/NVIDIA) → [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) → [PR #2054](https://github.com/boykopovar/AnyPS5/pull/2054) → [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) → [PR #425](https://github.com/boykopovar/AnyPS5/pull/425) → [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) |
| `PPSA99005` | ps5-opengl showcase | First draw (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) |
| `PPSA34356` | Marsupilami: Hoobadventure | Starts (mined) | Windows · PR #2558 | — |
| `PPSA05510` | Minecraft Legends | Starts (mined) | PR #1405 | — |
| `PPSA01317` |  | Starts (mined) | Windows · NVIDIA · PR #2583 | — |
| `PPSA02530` | PRAGMATA | Starts (mined) | Windows · PR #369 | — |
| `PPSA13934` | Spirit of the Island | Starts (mined) | Windows · PR #696 | — |
| `PPSA02262` | Dying Light 2 | Starts (mined) | Windows · NVIDIA · PR #1830 | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) |
| `PPSA33286` | Silent Hill: Townfall | Starts (mined) | Windows · NVIDIA · main | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2747](https://github.com/boykopovar/AnyPS5/issues/2747) |
| `PPSA99600` | Cloud Play | Converts (mined) | Windows · main | — |
| `PPSA99039` | EVO-PLAYER | Converts (mined) | Windows · PR #2932 | — |
| `PPSA99082` | OpenNOW | Converts (mined) | Windows · main | — |
| `PPSA99728` | OpenRCT2 Native Port | Converts (mined) | Windows · PR #2933 | — |
| `PPSA99764` | Porpoise | Converts (mined) | Linux · PR #1987 | — |
| `PPSA13427` |  | Converts (mined) | Linux · NVIDIA · PR #1481 | — |
| `PPSA69420` | ScreenTester5 | Converts (mined) | Windows · NVIDIA · PR #2332 | — |
| `PPSA03306` | Silt | Converts (mined) | Windows · NVIDIA · PR #1243 | — |
| `PPSA21607` | Smurfs Dreams | Converts (mined) | Windows · PR #911 | — |
| `PPSA74126` | Stremio Plus | Converts (mined) | Windows · PR #2934 | — |
| `PPSA25344` | Sword of the Sea | Converts (mined) | Windows · PR #2412 | — |
| `PPSA99515` | Emby5 | Converts (mined) | Linux · main | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) |
| `PPSA99505` | Jelly5 | Converts (mined) | Linux · main | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) |
| `PPSA99009` | ProsperoLichess | Converts (mined) | Windows · main | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) |
| `PPSA99002` | ProsperoLight | Converts (mined) | Windows · main | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) |
| `PPSA99001` | ProsperoRadio | Converts (mined) | Windows · main | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) |
| `PPSA99000` | ProsperoStore | Converts (mined) | PR #2906 | [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) |
| `PPSA99003` | ProsperoTV | Converts (mined) | Windows · main | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) |
| `PPSA97510` | PSXS5 | Converts (mined) | Windows · main | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6091750552) |
| `PPSA68091` | Ruffle Flash | Converts (mined) | Windows · main | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA19111` | XashPS5 | Converts (mined) | Windows · main | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) |
| `PPSA99007` | Yamagi Quake II | Converts (mined) | Windows · main | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA15508` | Last of Us Part II Remastered | Converts (mined) | Windows · NVIDIA · PR #2830 | [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) → [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) |
| `PPSA11386` | 007 First Light | Converts (mined) | Windows · NVIDIA · PR #2830 | [PR #2471](https://github.com/boykopovar/AnyPS5/pull/2471) → [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) → [#2642](https://github.com/boykopovar/AnyPS5/issues/2642) → [#2774](https://github.com/boykopovar/AnyPS5/issues/2774) |
| `PPSA92280` | Capy Mobile | — |  | [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) |
| `PPSA34547` | Control Resonant | — |  | [#2689](https://github.com/boykopovar/AnyPS5/issues/2689) |
| `PPSA06465` | Cult of the Lamb | — |  | [#2686](https://github.com/boykopovar/AnyPS5/issues/2686) |
| `PPSA03355` | Hades | — |  | [#2724](https://github.com/boykopovar/AnyPS5/issues/2724) |
| `PPSA01521` | Horizon Forbidden West | — |  | [#2809](https://github.com/boykopovar/AnyPS5/issues/2809) |
| `PPSA01746` | Kena: Bridge of Spirits | — |  | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA01802` | Kena: Bridge of Spirits | — |  | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA10261` | Lies of P | — |  | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA99109` | Prospero Explorer | — |  | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA99110` | Prospero Multi Tools | — |  | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA28502` | Pure Pool Pro | — |  | [#1455](https://github.com/boykopovar/AnyPS5/issues/1455) |
| `PPSA07411` | Resident Evil 4 | — |  | [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) |
| `PPSA04540` | Rise of the Ronin | — |  | [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) |
| `PPSA07286` | Road of Death | — |  | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) |
| `PPSA03001` | Sifu | — |  | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) |
| `PPSA10112` | Silent Hill: The Short Message | — |  | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) |
| `PPSA99902` | Sonic Unleashed Recompiled | — |  | [#2886](https://github.com/boykopovar/AnyPS5/issues/2886) |
| `PPSA23126` | Palworld | — |  | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) → [#2648](https://github.com/boykopovar/AnyPS5/issues/2648) |
| `PPSA01474` | Ratchet & Clank: Rift Apart | — |  | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) → [#2687](https://github.com/boykopovar/AnyPS5/issues/2687) |

## Coverage

- RDNA ISA decode: 1166 of 1166 (100.0%)
- HLE functions: 2708 of 3202 (84.57%)
- PM4 type-3 packets: 35 handled, 4 conditional, 16 rejected of 55

| Opcode | Packet | Status | Reason | Issues |
|---|---|---|---|---|
| `0x24` | `DRAW_INDIRECT` | conditional | rejected only when IndirectDrawsDisabled(): graphics draw, shader stages and guest render-target materialization are not implemented | #1895 |
| `0x25` | `DRAW_INDEX_INDIRECT` | conditional | rejected only when IndirectDrawsDisabled(): graphics draw, shader stages and guest render-target materialization are not implemented | #1895 |
| `0x2C` | `DRAW_INDIRECT_MULTI` | conditional | rejected only when IndirectDrawsDisabled(): graphics draw, shader stages and guest render-target materialization are not implemented |  |
| `0x33` | `INDIRECT_BUFFER_CNST` | rejected | nested command buffers, branching and nested flip reservation are not implemented |  |
| `0x39` | `MEM_SEMAPHORE` | rejected | cooperative command-queue waits are not implemented |  |
| `0x38` | `DRAW_INDEX_INDIRECT_MULTI` | conditional | rejected only when IndirectDrawsDisabled(): graphics draw, shader stages and guest render-target materialization are not implemented | #1895 |
| `0x3A` | `DISPATCH_DRAW_PREAMBLE` | rejected | graphics draw, shader stages and guest render-target materialization are not implemented |  |
| `0x3F` | `INDIRECT_BUFFER` | rejected | nested command buffers, branching and nested flip reservation are not implemented | #1458 |
| `0x41` | `CP_DMA` | rejected | opcode is named but has no handler in the reference dispatch table |  |
| `0x43` | `SURFACE_SYNC` | rejected | guest cache actions, GPU events and interrupt delivery are not implemented |  |
| `0x47` | `EVENT_WRITE_EOP` | rejected | guest cache actions, GPU events and interrupt delivery are not implemented | #1034 |
| `0x48` | `EVENT_WRITE_EOS` | rejected | guest cache actions, GPU events and interrupt delivery are not implemented |  |
| `0x68` | `SET_CONFIG_REG` | rejected | opcode is named but has no handler in the reference dispatch table |  |
| `0x78` | `SET_QUEUE_REG` | rejected | opcode is named but has no handler in the reference dispatch table |  |
| `0x84` | `INCREMENT_CE_COUNTER` | rejected | separate CE/DE execution and counter synchronization are not implemented |  |
| `0x85` | `INCREMENT_DE_COUNTER` | rejected | separate CE/DE execution and counter synchronization are not implemented |  |
| `0x86` | `WAIT_ON_CE_COUNTER` | rejected | separate CE/DE execution and counter synchronization are not implemented |  |
| `0x88` | `WAIT_ON_DE_COUNTER_DIFF` | rejected | separate CE/DE execution and counter synchronization are not implemented |  |
| `0x8D` | `DISPATCH_DRAW` | rejected | graphics draw, shader stages and guest render-target materialization are not implemented |  |
| `0x8E` | `GET_LOD_STATS` | rejected | GPU LOD statistics are not implemented; synthetic results are forbidden |  |
| `NOP·0x05` | `DRAW_RESET` | rejected | custom packet has no implemented contract | #1581 |
| `NOP·0x14` | `ACQUIRE_MEM_CUSTOM` | rejected | guest cache actions and GPU release events are not implemented |  |
| `NOP·0x15` | `WRITE_DATA_CUSTOM` | rejected | custom packet has no implemented contract |  |
| `NOP·0x18` | `RELEASE_MEM_CUSTOM` | rejected | guest cache actions and GPU release events are not implemented |  |
| `NOP·0x19` | `DMA_DATA_CUSTOM` | rejected | custom packet has no implemented contract |  |

Missing HLE functions named in issues:

- `libSceAgc`: `sceAgcAcbAtomicGds_0900` (#2591)
- `libSceAgc`: `sceAgcAcbSetFlip` (#1941, #2591)
- `libSceAgc`: `sceAgcAcbSetWorkloadComplete` (#2591)
- `libSceAgc`: `sceAgcAcbSetWorkloadStreamInactive` (#2591)
- `libSceAgc`: `sceAgcAcbSetWorkloadsActive` (#2591)
- `libSceAgc`: `sceAgcAcbWaitUntilSafeForRendering` (#1941, #2591, #2726)
- `libSceAgc`: `sceAgcBranchPatchSetElseTarget_0300` (#2591)
- `libSceAgc`: `sceAgcBranchPatchSetThenTarget_0300` (#1967, #2591)
- `libSceAgc`: `sceAgcDcbA_zARR5aCmkoY` (#2591)
- `libSceAgc`: `sceAgcDcbBeginOcclusionQueryGetSize` (#2591)
- `libSceAgc`: `sceAgcDcbEndOcclusionQueryGetSize` (#2591)
- `libSceAgc`: `sceAgcDcbSetIndexIndirectArgs` (#360, #2591)
- `libSceAgc`: `sceAgcDcbSetIndexIndirectArgsGetSize` (#2591)
- `libSceAgc`: `sceAgcDcbSetWorkloadComplete` (#2591)
- `libSceAgc`: `sceAgcDcbSetWorkloadStreamInactive` (#2591)
- `libSceAgc`: `sceAgcDcbSetWorkloadsActive` (#2591)
- `libSceAgc`: `sceAgcDebugRaiseException` (#1578, #1941, #1967, #2523)
- `libSceAgc`: `sceAgcGetDefaultCxStateFlat` (#1941, #2591)
- `libSceAgc`: `sceAgcSetSemaphoreMemory` (#1013)
- `libSceAgc`: `sceAgcUpdateInterpolantMapping_0100` (#2591)
- `libSceVoiceQoS`: `sceVoiceQoSConnect` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSCreateLocalEndpoint` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSCreateRemoteEndpoint` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSDeleteLocalEndpoint` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSDeleteRemoteEndpoint` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSDisconnect` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSEnd` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSGetLocalEndpointAttribute` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSReadPacket` (#1967, #2598)
- `libSceVoiceQoS`: `sceVoiceQoSSetLocalEndpointAttribute` (#1967, #2598)

## Help wanted

- [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) Packed pixel ancillary word read whole after its VGPR is reused: Test AlxcBTW/AnyPS5#25 on Stray, LEGO Horizon, Kena and Lies of P and report which shaders still fail.
- [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) pthread_sigmask is not exported (libkernel): Needs an author who passes the PR intake rule, or a maintainer to reopen #2106.
- [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) pthread_set_name_np is not exported (libkernel): First open blocker for 2 titles; no open fix PR
- [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) Layered rendering: color views of several array slices: First open blocker for 3 titles; no open fix PR
- [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) v_interp_mov P10/P20 of a flat input without pass-through: Hardware answer needed (tools/hw-oracle on a PS5-class GPU).
- [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) Dying Light 2 (PPSA02262) on Windows: what stops it between conversion and its own startup: First open blocker for 2 titles; no open fix PR
- [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) libkernel: support kern.sdk_version in sysctlbyname (Capy Mobile PPSA92280): First open blocker for 1 title; no open fix PR
- [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) Ratchet & Clank: Rift Apart: a registered pixel shader is drawn with DB_SHADER_CONTROL=0 while its header sets 0x20601: First open blocker for 1 title; no open fix PR
- [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) ProsperoStore (PPSA99000): startup stop on unresolved sceKernelGetSystemSwVersion: First open blocker for 1 title; no open fix PR
- [#2809](https://github.com/boykopovar/AnyPS5/issues/2809) HFW loading: fixed host-import budget forces a multi-GiB heap mirror and OOM: First open blocker for 1 title; no open fix PR
- [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) Resident Evil 4 (PPSA07411): start-up needs a library named Party.prx; with the missing exports added it stops at sce::Json::InitParameter2::setSpecialFloatFormatType: First open blocker for 1 title; no open fix PR
- [#2724](https://github.com/boykopovar/AnyPS5/issues/2724) Hades (PPSA03355) on Windows: start-up faults in the title's own libc.prx before any file is opened: First open blocker for 1 title; no open fix PR

## Known gaps

- Title names, engines and stages are mined with keyword rules per line; negation and context are handled only roughly.
- Mined chain order is a heuristic: the latest recorded stop first, then issues by creation date.
- PR comments and review threads are not read; only PR titles and bodies are.
- Titles without a PPSA ID (some homebrew) appear only when curated.
- Discord reports are invisible unless someone copies them into GitHub or the curated file.
- Signatures are matched by prefix after hex addresses and long numbers are masked; reworded messages split into separate keys.
- PM4 status reads Pm4::UnsupportedReason(); a packet can pass that check and still be emulated partially.
- Stages mined from PR bodies describe the PR branch (build “PR #N”), not main.
- An issue that names seven or more titles is treated as a tracker: only its per-title stop rows count, as separate blockers.
- HLE “named in issues” counts any mention of a missing function, including lists of imports that were never reached.

