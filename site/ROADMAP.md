# AnyPS5 blocker map

> Generated data, community prototype, not official. Built 2026-10-10T21:43:48Z from public GitHub data of [boykopovar/AnyPS5](https://github.com/boykopovar/AnyPS5) at `262c0316` plus `data/blockers.json`.

Issues read: 304 · PRs read: 2692 · titles: 164 · open blockers: 71 (61 block at least one title) · curated blockers: 15

Score = 3 × one_fix_away + 2 × frontier + total. Frontier: titles for which the blocker is the first open one. One fix away: titles for which it is the only open one.

## Focus areas

1. **libkernel** (score 102): 14 blockers on 19 titles, first stop for 18; open fix PRs 3. Top: [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106), [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482), [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872), [#1794](https://github.com/boykopovar/AnyPS5/issues/1794)
2. **Shader recompiler** (score 67): 12 blockers on 16 titles, first stop for 12; open fix PRs 6. Top: [#2548](https://github.com/boykopovar/AnyPS5/issues/2548), [#1413](https://github.com/boykopovar/AnyPS5/issues/1413), [#2621](https://github.com/boykopovar/AnyPS5/issues/2621), [#2783](https://github.com/boykopovar/AnyPS5/issues/2783)
3. **AGC driver** (score 61): 15 blockers on 15 titles, first stop for 11; open fix PRs 2. Top: [#1409](https://github.com/boykopovar/AnyPS5/issues/1409), [#2102](https://github.com/boykopovar/AnyPS5/issues/2102), [#3055](https://github.com/boykopovar/AnyPS5/issues/3055), [#2942](https://github.com/boykopovar/AnyPS5/issues/2942)
4. **libc** (score 24): 3 blockers on 4 titles, first stop for 4; open fix PRs 3. Top: [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578), [#3032](https://github.com/boykopovar/AnyPS5/issues/3032), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382)
5. **HLE libraries** (score 20): 4 blockers on 5 titles, first stop for 3; open fix PRs 1. Top: [#2701](https://github.com/boykopovar/AnyPS5/issues/2701), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578), [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382), [#2776](https://github.com/boykopovar/AnyPS5/issues/2776)

## Blocker ranking

| # | Blocker | Frontier | One fix away | Total | Score | Area | PRs | Last activity |
|--:|---|--:|--:|--:|--:|---|---|---|
| 1 | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) Packed pixel ancillary word read whole after its VGPR is reused (curated) | 6 | 5 | 6 | **33** | Shader recompiler | [AlxcBTW#25](https://github.com/AlxcBTW/AnyPS5/pull/25) open, [#2589](https://github.com/boykopovar/AnyPS5/pull/2589) open, [AlxcBTW#30](https://github.com/AlxcBTW/AnyPS5/pull/30) open, [#2872](https://github.com/boykopovar/AnyPS5/pull/2872) merged | 2026-10-10 |
| 2 | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) pthread_sigmask is not exported (libkernel) (curated) | 5 | 5 | 6 | **31** | libkernel | [#2106](https://github.com/boykopovar/AnyPS5/pull/2106) closed | 2026-10-10 |
| 3 | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) Road of Death (PPSA07286) fails on startup: missing libSceXml.prx (mined) | 4 | 2 | 4 | **18** | — | [#2872](https://github.com/boykopovar/AnyPS5/pull/2872) merged, [#2658](https://github.com/boykopovar/AnyPS5/pull/2658) closed, [#1808](https://github.com/boykopovar/AnyPS5/pull/1808) closed | 2026-10-10 |
| 4 | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) Storage image access to a depth/stencil surface (curated) | 2 | 2 | 3 | **13** | AGC driver | [#454](https://github.com/boykopovar/AnyPS5/pull/454) open, [#2519](https://github.com/boykopovar/AnyPS5/pull/2519) closed, [#1495](https://github.com/boykopovar/AnyPS5/pull/1495) merged, [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open | 2026-10-10 |
| 5 | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) _umtx_op wait and wake are not implemented (curated) | 2 | 2 | 3 | **13** | libkernel | [#1482](https://github.com/boykopovar/AnyPS5/pull/1482) open | 2026-10-10 |
| 6 | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) pthread_set_name_np is not exported (libkernel) (curated) | 2 | 2 | 3 | **13** | libkernel | [#1872](https://github.com/boykopovar/AnyPS5/pull/1872) closed | 2026-10-10 |
| 7 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) atoll (fLcU5G6Qrjs) is not exported by libSceLibcInternal (mined) | 2 | 2 | 2 | **12** | libc | [#2932](https://github.com/boykopovar/AnyPS5/pull/2932) open, [#2186](https://github.com/boykopovar/AnyPS5/pull/2186) closed, [#1852](https://github.com/boykopovar/AnyPS5/pull/1852) closed, [#1591](https://github.com/boykopovar/AnyPS5/pull/1591) closed | 2026-10-10 |
| 8 | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) Layered rendering: color views of several array slices (curated) | 3 | 0 | 4 | **10** | AGC driver | [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open, [#1940](https://github.com/boykopovar/AnyPS5/pull/1940) open, [#1077](https://github.com/boykopovar/AnyPS5/pull/1077) open, [#425](https://github.com/boykopovar/AnyPS5/pull/425) open | 2026-10-10 |
| 9 | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) v_interp_mov P10/P20 of a flat input without pass-through (curated) | 3 | 0 | 3 | **9** | Shader recompiler | [AlxcBTW#12](https://github.com/AlxcBTW/AnyPS5/pull/12) open, [#2626](https://github.com/boykopovar/AnyPS5/pull/2626) merged, [#1412](https://github.com/boykopovar/AnyPS5/pull/1412) merged, [#1196](https://github.com/boykopovar/AnyPS5/pull/1196) merged | 2026-10-10 |
| 10 | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) Dying Light 2 (PPSA02262) on Windows: what stops it between conversion and its own startup (mined) | 2 | 1 | 2 | **9** | libkernel | [#1091](https://github.com/boykopovar/AnyPS5/pull/1091) open, [#2129](https://github.com/boykopovar/AnyPS5/pull/2129) merged, [#1830](https://github.com/boykopovar/AnyPS5/pull/1830) merged, [#1803](https://github.com/boykopovar/AnyPS5/pull/1803) merged | 2026-10-10 |
| 11 | [#3043](https://github.com/boykopovar/AnyPS5/issues/3043) PRAGMATA (PPSA02530 v01.200.000) on Windows: the title's libc rejects its allocator's mspace buffer in the ASLR-relocated image above 1 TiB, so the first malloc returns NULL and start-up faults (mined) | 1 | 1 | 2 | **7** | — | [#1958](https://github.com/boykopovar/AnyPS5/pull/1958) merged, [#1808](https://github.com/boykopovar/AnyPS5/pull/1808) closed | 2026-10-10 |
| 12 | [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) libkernel: support kern.sdk_version in sysctlbyname (Capy Mobile PPSA92280) (mined) | 1 | 1 | 2 | **7** | HLE libraries | [#2967](https://github.com/boykopovar/AnyPS5/pull/2967) open, [#2753](https://github.com/boykopovar/AnyPS5/pull/2753) closed, [#2697](https://github.com/boykopovar/AnyPS5/pull/2697) closed, [#2024](https://github.com/boykopovar/AnyPS5/pull/2024) closed | 2026-10-10 |
| 13 | [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) Ratchet & Clank: Rift Apart: a registered pixel shader is drawn with DB_SHADER_CONTROL=0 while its header sets 0x20601 (mined) | 1 | 1 | 2 | **7** | Shader recompiler | [#757](https://github.com/boykopovar/AnyPS5/pull/757) open, [#1988](https://github.com/boykopovar/AnyPS5/pull/1988) merged, [#1902](https://github.com/boykopovar/AnyPS5/pull/1902) merged, [#1836](https://github.com/boykopovar/AnyPS5/pull/1836) merged | 2026-10-10 |
| 14 | [#3055](https://github.com/boykopovar/AnyPS5/issues/3055) AGC: GTA V libSceJobManager compute kernel reads its V#s from a block that is still all 0xFF at capture (mined) | 1 | 1 | 1 | **6** | AGC driver | none | 2026-10-10 |
| 15 | [#3032](https://github.com/boykopovar/AnyPS5/issues/3032) libc: implement vsnprintf_s and vsscanf_s (PPSA04029); fix branch ready (mined) | 1 | 1 | 1 | **6** | libc | [#3046](https://github.com/boykopovar/AnyPS5/pull/3046) open, [#2301](https://github.com/boykopovar/AnyPS5/pull/2301) merged, [#3030](https://github.com/boykopovar/AnyPS5/pull/3030) closed | 2026-10-10 |
| 16 | [#2942](https://github.com/boykopovar/AnyPS5/issues/2942) Launching Silksong Failed (mined) | 1 | 1 | 1 | **6** | AGC driver | [#419](https://github.com/boykopovar/AnyPS5/pull/419) open | 2026-10-10 |
| 17 | [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) ProsperoStore (PPSA99000): startup stop on unresolved sceKernelGetSystemSwVersion (mined) | 1 | 1 | 1 | **6** | libkernel | [#2945](https://github.com/boykopovar/AnyPS5/pull/2945) open, [#2543](https://github.com/boykopovar/AnyPS5/pull/2543) merged, [#2906](https://github.com/boykopovar/AnyPS5/pull/2906) closed | 2026-10-10 |
| 18 | [#2809](https://github.com/boykopovar/AnyPS5/issues/2809) HFW loading: fixed host-import budget forces a multi-GiB heap mirror and OOM (mined) | 1 | 1 | 1 | **6** | AGC driver | [#290](https://github.com/boykopovar/AnyPS5/pull/290) open, [#1616](https://github.com/boykopovar/AnyPS5/pull/1616) closed | 2026-10-10 |
| 19 | [#2724](https://github.com/boykopovar/AnyPS5/issues/2724) Hades (PPSA03355) on Windows: start-up faults in the title's own libc.prx before any file is opened (mined) | 1 | 1 | 1 | **6** | libkernel | [#1091](https://github.com/boykopovar/AnyPS5/pull/1091) open, [#846](https://github.com/boykopovar/AnyPS5/pull/846) open, [#2276](https://github.com/boykopovar/AnyPS5/pull/2276) merged, [#1798](https://github.com/boykopovar/AnyPS5/pull/1798) merged | 2026-10-10 |
| 20 | [#2686](https://github.com/boykopovar/AnyPS5/issues/2686) Cult of the Lamb (PPSA06465): start-up stops on unresolved import pXJh3aVk8Ks (sceContentDeleteById) (mined) | 1 | 1 | 1 | **6** | libkernel | [#846](https://github.com/boykopovar/AnyPS5/pull/846) open, [#2623](https://github.com/boykopovar/AnyPS5/pull/2623) merged, [#2740](https://github.com/boykopovar/AnyPS5/pull/2740) closed | 2026-10-10 |
| 21 | [#2552](https://github.com/boykopovar/AnyPS5/issues/2552) Demon's Souls crashes 14 s after launch with a guest null read when built with ANYPS5_ENABLE_SPIRV_TOOLS=OFF (the default) (mined) | 1 | 1 | 1 | **6** | AGC driver | [#1186](https://github.com/boykopovar/AnyPS5/pull/1186) open, [#861](https://github.com/boykopovar/AnyPS5/pull/861) merged | 2026-10-10 |
| 22 | [#1973](https://github.com/boykopovar/AnyPS5/issues/1973) Demons Souls v1.04 PPSA01342 Segfault upon running linked elf (mined) | 1 | 1 | 1 | **6** | — | [#3](https://github.com/boykopovar/AnyPS5/pull/3) merged, [#2](https://github.com/boykopovar/AnyPS5/pull/2) merged, [#12](https://github.com/boykopovar/AnyPS5/pull/12) closed | 2026-10-09 |
| 23 | [#1930](https://github.com/boykopovar/AnyPS5/issues/1930) Linux: PPSA28997 (Sons of Sparta) aborts at start-up with "RTLD application heap: cannot replace an active allocator" (#693 regressed after #1515) (mined) | 1 | 1 | 1 | **6** | libkernel | [#1482](https://github.com/boykopovar/AnyPS5/pull/1482) open, [#1515](https://github.com/boykopovar/AnyPS5/pull/1515) merged, [#1156](https://github.com/boykopovar/AnyPS5/pull/1156) merged, [#1102](https://github.com/boykopovar/AnyPS5/pull/1102) merged | 2026-10-10 |
| 24 | [#1497](https://github.com/boykopovar/AnyPS5/issues/1497) Linux: a bundled libc.prx loader shim (ps5-native-app-boilerplate) binds libc imports to placeholder exports; DOOM PPSA99666 finds no WAD (mined) | 1 | 1 | 1 | **6** | Relinker | [#1529](https://github.com/boykopovar/AnyPS5/pull/1529) open, [#2932](https://github.com/boykopovar/AnyPS5/pull/2932) open, [#2332](https://github.com/boykopovar/AnyPS5/pull/2332) open, [#1307](https://github.com/boykopovar/AnyPS5/pull/1307) open | 2026-10-10 |
| 25 | [#1455](https://github.com/boykopovar/AnyPS5/issues/1455) Startup crash: display interface built with a null backend pointer (mined) | 1 | 1 | 1 | **6** | — | [#1630](https://github.com/boykopovar/AnyPS5/pull/1630) closed | 2026-10-09 |
| 26 | [#1034](https://github.com/boykopovar/AnyPS5/issues/1034) Balatro PPSA21402 on Windows: the title overwrites its own register lists when more than 2 flips are pending (VIDEO_OUT_FLIP_QUEUE_CAPACITY is 16) (mined) | 1 | 1 | 1 | **6** | — | [#2219](https://github.com/boykopovar/AnyPS5/pull/2219) merged, [#1745](https://github.com/boykopovar/AnyPS5/pull/1745) merged, [#1597](https://github.com/boykopovar/AnyPS5/pull/1597) merged, [#1534](https://github.com/boykopovar/AnyPS5/pull/1534) merged | 2026-10-10 |
| 27 | [#1033](https://github.com/boykopovar/AnyPS5/issues/1033) Marvels Wolverine PPSA03671 Relies on consoles .prxs (mined) | 1 | 1 | 1 | **6** | — | [#1461](https://github.com/boykopovar/AnyPS5/pull/1461) merged, [#1317](https://github.com/boykopovar/AnyPS5/pull/1317) merged, [#2390](https://github.com/boykopovar/AnyPS5/pull/2390) closed, [#28](https://github.com/boykopovar/AnyPS5/pull/28) closed | 2026-10-10 |
| 28 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) Module libSceOpusDec.prx is missing (mined) | 1 | 1 | 1 | **6** | HLE libraries | none | 2026-10-08 |
| 29 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) gethostname (-nvxBWa0iDs) is not exported (mined) | 1 | 1 | 1 | **6** | libc | [#2968](https://github.com/boykopovar/AnyPS5/pull/2968) open, [#2019](https://github.com/boykopovar/AnyPS5/pull/2019) closed, [#1975](https://github.com/boykopovar/AnyPS5/pull/1975) closed, [#1594](https://github.com/boykopovar/AnyPS5/pull/1594) closed | 2026-10-10 |
| 30 | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) arc4random_buf (n1KOc0lTUEs) is not exported (mined) | 1 | 1 | 1 | **6** | HLE libraries | [#2865](https://github.com/boykopovar/AnyPS5/pull/2865) open, [#1637](https://github.com/boykopovar/AnyPS5/pull/1637) closed | 2026-10-10 |
| 31 | [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) NVIDIA: wave64 NGG culling program reads lane 63 (curated) | 1 | 0 | 2 | **4** | Shader recompiler | [#1825](https://github.com/boykopovar/AnyPS5/pull/1825) open, [AlxcBTW#25](https://github.com/AlxcBTW/AnyPS5/pull/25) open | 2026-10-10 |
| 32 | [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) 007 First Light (PPSA11386) on Linux: start-up stops in order and the PRs that pass them (mined) | 1 | 0 | 2 | **4** | AGC driver | [#2974](https://github.com/boykopovar/AnyPS5/pull/2974) open, [#2813](https://github.com/boykopovar/AnyPS5/pull/2813) open, [#2589](https://github.com/boykopovar/AnyPS5/pull/2589) open, [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open | 2026-10-10 |
| 33 | [PR #2471](https://github.com/boykopovar/AnyPS5/pull/2471) Structurizer: selections joined at a shared loop exit (curated) | 1 | 0 | 1 | **3** | Shader recompiler | [#2471](https://github.com/boykopovar/AnyPS5/pull/2471) draft | 2026-10-10 |
| 34 | [siglongjmp](https://github.com/boykopovar/AnyPS5/issues/1578) siglongjmp is not exported (libkernel) (curated) | 1 | 0 | 1 | **3** | libkernel | none | — |
| 35 | [#2886](https://github.com/boykopovar/AnyPS5/issues/2886) libkernel: Windows lstat misreports symbolic links instead of throwing (mined) | 1 | 0 | 1 | **3** | libkernel | [#2898](https://github.com/boykopovar/AnyPS5/pull/2898) open, [#1624](https://github.com/boykopovar/AnyPS5/pull/1624) merged | 2026-10-10 |
| 36 | [#2811](https://github.com/boykopovar/AnyPS5/issues/2811) libSceNet Sockets implementation issue (mined) | 1 | 0 | 1 | **3** | — | none | 2026-10-10 |
| 37 | [#2715](https://github.com/boykopovar/AnyPS5/issues/2715) Ghost of Yōtei: compute shader 0x80003aa700 loads its T# from a buffer at an index read from another buffer in a loop (GetImageResource dword 0 is not a valid runtime value) (mined) | 1 | 0 | 1 | **3** | Shader recompiler | [#1940](https://github.com/boykopovar/AnyPS5/pull/1940) open, [#822](https://github.com/boykopovar/AnyPS5/pull/822) open, [#758](https://github.com/boykopovar/AnyPS5/pull/758) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open | 2026-10-10 |
| 38 | [#2476](https://github.com/boykopovar/AnyPS5/issues/2476) Windows: Astro's Playroom (PPSA01325) fails to load libSceJobManager.prx (error 126) (mined) | 1 | 0 | 1 | **3** | — | [#2924](https://github.com/boykopovar/AnyPS5/pull/2924) closed | 2026-10-10 |
| 39 | [#865](https://github.com/boykopovar/AnyPS5/issues/865) agc-driver: storage image write-back drops GPU results for CPU-stamped 64 KiB edge blocks (boxes in Silksong's menu text) (mined) | 1 | 0 | 1 | **3** | libkernel | [#1482](https://github.com/boykopovar/AnyPS5/pull/1482) open, [#846](https://github.com/boykopovar/AnyPS5/pull/846) open, [#1599](https://github.com/boykopovar/AnyPS5/pull/1599) merged, [#1495](https://github.com/boykopovar/AnyPS5/pull/1495) merged | 2026-10-10 |
| 40 | [#665](https://github.com/boykopovar/AnyPS5/issues/665) AGC sampler: border colour table (BORDER_COLOR_TYPE 3) not implemented (mined) | 1 | 0 | 1 | **3** | AGC driver | [#1221](https://github.com/boykopovar/AnyPS5/pull/1221) closed, [#941](https://github.com/boykopovar/AnyPS5/pull/941) merged, [#668](https://github.com/boykopovar/AnyPS5/pull/668) merged, [#2392](https://github.com/boykopovar/AnyPS5/pull/2392) closed | 2026-10-10 |
| 41 | [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) v_fma_mix* in FLOAT_MODE 0xcc (f16 round toward zero) (curated) | 0 | 0 | 2 | **2** | Shader recompiler | [AlxcBTW#19](https://github.com/AlxcBTW/AnyPS5/pull/19) open, [#1482](https://github.com/boykopovar/AnyPS5/pull/1482) open, [#2627](https://github.com/boykopovar/AnyPS5/pull/2627) merged, [#2626](https://github.com/boykopovar/AnyPS5/pull/2626) merged | 2026-10-10 |
| 42 | [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) Recompiler: f32 product tininess is checked before rounding (RDNA2 checks after), and the check makes float-heavy shaders slow to compile (mined) | 0 | 0 | 2 | **2** | Shader recompiler | [#18](https://github.com/boykopovar/AnyPS5/pull/18) closed | 2026-10-10 |
| 43 | [#2642](https://github.com/boykopovar/AnyPS5/issues/2642) Structurizer: shared merge splitting never terminates in a two-latch loop (curated) | 0 | 0 | 1 | **1** | Shader recompiler | [AlxcBTW#20](https://github.com/AlxcBTW/AnyPS5/pull/20) closed, [AlxcBTW#24](https://github.com/AlxcBTW/AnyPS5/pull/24) open, [#2974](https://github.com/boykopovar/AnyPS5/pull/2974) open, [#2471](https://github.com/boykopovar/AnyPS5/pull/2471) draft | 2026-10-10 |
| 44 | [PR #2054](https://github.com/boykopovar/AnyPS5/pull/2054) Windows: direct memory mapped one 16 KiB view at a time (curated) | 0 | 0 | 1 | **1** | libkernel | [#2054](https://github.com/boykopovar/AnyPS5/pull/2054) open | 2026-10-10 |
| 45 | [PR #425](https://github.com/boykopovar/AnyPS5/pull/425) Depth surface sampled as a cube texture (curated) | 0 | 0 | 1 | **1** | AGC driver | [#425](https://github.com/boykopovar/AnyPS5/pull/425) open | 2026-10-10 |
| 46 | [#3037](https://github.com/boykopovar/AnyPS5/issues/3037) AGC: BDA written-page tracking overflows at capacity or after eight colliding pages (mined) | 0 | 0 | 1 | **1** | AGC driver | [#2756](https://github.com/boykopovar/AnyPS5/pull/2756) open, [#1825](https://github.com/boykopovar/AnyPS5/pull/1825) open, [#1280](https://github.com/boykopovar/AnyPS5/pull/1280) merged, [#1265](https://github.com/boykopovar/AnyPS5/pull/1265) merged | 2026-10-10 |
| 47 | [#3036](https://github.com/boykopovar/AnyPS5/issues/3036) AGC: sampled 2D MSAA image has no descriptor shape (PPSA99902 conditional startup) (mined) | 0 | 0 | 1 | **1** | AGC driver | [#2756](https://github.com/boykopovar/AnyPS5/pull/2756) open, [#2015](https://github.com/boykopovar/AnyPS5/pull/2015) open, [#1825](https://github.com/boykopovar/AnyPS5/pull/1825) open, [#1732](https://github.com/boykopovar/AnyPS5/pull/1732) open | 2026-10-10 |
| 48 | [#2970](https://github.com/boykopovar/AnyPS5/issues/2970) AGC: SW_64KB_D_X color target refused during PPSA99902 conditional startup (mined) | 0 | 0 | 1 | **1** | AGC driver | [#1825](https://github.com/boykopovar/AnyPS5/pull/1825) open, [#1732](https://github.com/boykopovar/AnyPS5/pull/1732) open, [#1189](https://github.com/boykopovar/AnyPS5/pull/1189) open, [#1077](https://github.com/boykopovar/AnyPS5/pull/1077) open | 2026-10-10 |
| 49 | [#2944](https://github.com/boykopovar/AnyPS5/issues/2944) AMD RX 6700 XT: 9 agc_driver execution tests segfault in amdvlk64, sdwa_float_selectors and sdwa_ldexp_f16 give wrong results (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-10 |
| 50 | [#2914](https://github.com/boykopovar/AnyPS5/issues/2914) Astro's Playroom (PPSA01325): shader ABI resolution passes a different Shader* header pointer for the same code (mined) | 0 | 0 | 1 | **1** | AGC driver | [#2969](https://github.com/boykopovar/AnyPS5/pull/2969) closed, [#2063](https://github.com/boykopovar/AnyPS5/pull/2063) merged | 2026-10-10 |
| 51 | [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) Resident Evil 4 (PPSA07411): start-up needs a library named Party.prx; with the missing exports added it stops at sce::Json::InitParameter2::setSpecialFloatFormatType (mined) | 0 | 0 | 1 | **1** | HLE libraries | [#1808](https://github.com/boykopovar/AnyPS5/pull/1808) closed | 2026-10-10 |
| 52 | [#2775](https://github.com/boykopovar/AnyPS5/issues/2775) Astro Bot: GPU hang (ring timeout) in a mesh-shader draw of 0x50000ab00, 40 workgroups, on RADV/RDNA4 (mined) | 0 | 0 | 1 | **1** | — | [#2653](https://github.com/boykopovar/AnyPS5/pull/2653) merged | 2026-10-10 |
| 53 | [#2774](https://github.com/boykopovar/AnyPS5/issues/2774) Recompiler: MemoryIndexBelongsTo walks the whole program on every call; about half of a warm start-up's CPU on 007 First Light (mined) | 0 | 0 | 1 | **1** | Shader recompiler | [#2813](https://github.com/boykopovar/AnyPS5/pull/2813) open, [#758](https://github.com/boykopovar/AnyPS5/pull/758) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open, [#1184](https://github.com/boykopovar/AnyPS5/pull/1184) draft | 2026-10-10 |
| 54 | [#2747](https://github.com/boykopovar/AnyPS5/issues/2747) Shader recompile fails on v_cvt_f16_u16 SDWA with a byte source select (Silent Hill: Townfall) (mined) | 0 | 0 | 1 | **1** | Shader recompiler | [#2838](https://github.com/boykopovar/AnyPS5/pull/2838) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open, [#2200](https://github.com/boykopovar/AnyPS5/pull/2200) merged, [#2695](https://github.com/boykopovar/AnyPS5/pull/2695) closed | 2026-10-10 |
| 55 | [#2648](https://github.com/boykopovar/AnyPS5/issues/2648) Palworld (PPSA23126): next start-up stop is unresolved import oiOi7vgPfAY (sceAudioOut2EnableChat) (mined) | 0 | 0 | 1 | **1** | libkernel | [#1091](https://github.com/boykopovar/AnyPS5/pull/1091) open, [#2623](https://github.com/boykopovar/AnyPS5/pull/2623) merged, [#2659](https://github.com/boykopovar/AnyPS5/pull/2659) closed | 2026-10-10 |
| 56 | [#2366](https://github.com/boykopovar/AnyPS5/issues/2366) Sampling a D16 depth surface's memory as a half-width 32-bit texture (PPSA15657): "sampling the depth plane ... is not implemented" (mined) | 0 | 0 | 1 | **1** | AGC driver | [#425](https://github.com/boykopovar/AnyPS5/pull/425) open, [#2022](https://github.com/boykopovar/AnyPS5/pull/2022) merged | 2026-10-10 |
| 57 | [#2365](https://github.com/boykopovar/AnyPS5/issues/2365) UE4 title (PPSA15657): LowLevelFatalError "RemoveFromOuterMap NumRemoved = 0" when the title screen opens the menu (mined) | 0 | 0 | 1 | **1** | — | [#2339](https://github.com/boykopovar/AnyPS5/pull/2339) merged | 2026-10-10 |
| 58 | [#2355](https://github.com/boykopovar/AnyPS5/issues/2355) TechnicalDebt evidence: PPSA26344 call sites for X+4jdIS75P0 and dbOlWdppb4o (unknown function info) (mined) | 0 | 0 | 1 | **1** | — | none | 2026-10-09 |
| 59 | [#1970](https://github.com/boykopovar/AnyPS5/issues/1970) agc-driver: write-back drops GPU results of full 64 KiB blocks of 1920x1080 render targets (PPSA12544 backgrounds garbled) (mined) | 0 | 0 | 1 | **1** | libkernel | [#1997](https://github.com/boykopovar/AnyPS5/pull/1997) closed, [#846](https://github.com/boykopovar/AnyPS5/pull/846) open, [#425](https://github.com/boykopovar/AnyPS5/pull/425) open, [#2791](https://github.com/boykopovar/AnyPS5/pull/2791) merged | 2026-10-10 |
| 60 | [#1920](https://github.com/boykopovar/AnyPS5/issues/1920) Ghost of Yōtei (PPSA26344): unsupported scalar source operand code 235 at program counter 856 (mined) | 0 | 0 | 1 | **1** | Shader recompiler | [#1940](https://github.com/boykopovar/AnyPS5/pull/1940) open, [#1190](https://github.com/boykopovar/AnyPS5/pull/1190) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open, [#1837](https://github.com/boykopovar/AnyPS5/pull/1837) merged | 2026-10-10 |
| 61 | [#479](https://github.com/boykopovar/AnyPS5/issues/479) AGC: SRT walker statically evaluates a scalar load behind a per-lane exec guard and fails on a NULL pointer (mined) | 0 | 0 | 1 | **1** | AGC driver | [#758](https://github.com/boykopovar/AnyPS5/pull/758) open, [#757](https://github.com/boykopovar/AnyPS5/pull/757) open, [#290](https://github.com/boykopovar/AnyPS5/pull/290) open, [#759](https://github.com/boykopovar/AnyPS5/pull/759) merged | 2026-10-10 |

## Titles

Best stage counts only verified stages: curated, upstream, or mined below Menus. A mined claim of Menus or higher that nobody has reviewed is listed as an unverified claim and is not sorted on.

| ID | Title | Best stage | Where | Source | Unverified claim | Open blockers, in order |
|---|---|---|---|---|---|---|
| `PPSA02929` | Dreaming Sarah | Playable (upstream) | Windows · main | [COMPATIBILITY.md](https://github.com/boykopovar/AnyPS5/blob/main/docs/user/COMPATIBILITY.md) | — | [#2944](https://github.com/boykopovar/AnyPS5/issues/2944) |
| `PPSA22520` | Animal Well | Menus (curated, reviewed) | Windows · main | [#964](https://github.com/boykopovar/AnyPS5/pull/964) | — | — |
| `PPSA04263` | Grand Theft Auto V | Menus (curated, reviewed) | main at the merge of #153 | [#153](https://github.com/boykopovar/AnyPS5/pull/153) | — | — |
| `PPSA21402` | Balatro | Menus (curated, reviewed) | Linux · NVIDIA · main + #1020, #861, #1038, #1100 (all merged by 2026-10-10) | [#1197](https://github.com/boykopovar/AnyPS5/pull/1197) | Ingame, [source](https://github.com/boykopovar/AnyPS5/issues/1034#issuecomment-6101737128) | [#1034](https://github.com/boykopovar/AnyPS5/issues/1034) |
| `PPSA01342` | Demon's Souls | Menus (curated, reviewed) | Windows · NVIDIA · main at the merge of #5 | [#5](https://github.com/boykopovar/AnyPS5/pull/5) | — | [#1973](https://github.com/boykopovar/AnyPS5/issues/1973) |
| `PPSA04264` | GTA V | Menus (curated, reviewed) | Windows · NVIDIA · main + #153 (merged) | [#167](https://github.com/boykopovar/AnyPS5/pull/167) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/493) | [#3055](https://github.com/boykopovar/AnyPS5/issues/3055) |
| `PPSA99920` | Prospero Vibrate | Menus (curated) | Windows · NVIDIA · main + #2821, #2106 and AlxcBTW#21 | [#2761](https://github.com/boykopovar/AnyPS5/issues/2761) | — | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA99050` | Homebrew UI Lab | Menus (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413 comment](https://github.com/boykopovar/AnyPS5/issues/1413#issuecomment-6095663977) | — | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) |
| `PPSA39410` | VITA5 | Menus (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413 comment](https://github.com/boykopovar/AnyPS5/issues/1413#issuecomment-6095663977) | — | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2682](https://github.com/boykopovar/AnyPS5/issues/2682) |
| `PPSA98001` | PokeMMO | Menus (curated) | Windows · NVIDIA · main + #1482, #2106, #1872, siglongjmp and AlxcBTW#19 | [#2631 comment](https://github.com/boykopovar/AnyPS5/issues/2631#issuecomment-6097885704) | — | [siglongjmp](https://github.com/boykopovar/AnyPS5/issues/1578) → [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) → [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) → [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) → [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) |
| `PPSA10698` | FPV Simulator | Presents (mined) | Windows · NVIDIA · main | [#2994](https://github.com/boykopovar/AnyPS5/issues/2994) | — | — |
| `PPSA36082` | Hades II | Presents (mined) | Linux · NVIDIA · PR #681 | [#681](https://github.com/boykopovar/AnyPS5/pull/681) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/1202#issuecomment-6081737193) | — |
| `PPSA29141` | LEGO Party! | Presents (mined) | Windows · NVIDIA · PR #2053 | [#2053](https://github.com/boykopovar/AnyPS5/pull/2053) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2052) | — |
| `PPSA09706` | Persona 5 Tactica | Presents (mined) | Windows · PR #1222 | [#1222](https://github.com/boykopovar/AnyPS5/pull/1222) | — | — |
| `PPSA01736` | Planet Coaster | Presents (mined) | Windows · NVIDIA · PR #2152 | [#2152](https://github.com/boykopovar/AnyPS5/pull/2152) | — | — |
| `PPSA07906` |  | Presents (mined) | Windows · NVIDIA · PR #1709 | [#1709](https://github.com/boykopovar/AnyPS5/pull/1709) | — | — |
| `PPSA59322` |  | Presents (mined) | Windows · AMD · PR #1732 | [#1732 comment](https://github.com/boykopovar/AnyPS5/pull/1732#issuecomment-6095296573) | — | — |
| `PPSA99006` | ProsperoPuzzles | Presents (mined) | Windows · NVIDIA · main | [#2026 comment](https://github.com/boykopovar/AnyPS5/issues/2026#issuecomment-6094252292) | — | — |
| `PPSA01289` | Sackboy: A Big Adventure | Presents (mined) | Windows · PR #2075 | [#2075](https://github.com/boykopovar/AnyPS5/pull/2075) | — | — |
| `PPSA12500` | Seeker: My Shadow | Presents (mined) | PR #425 | [#425 comment](https://github.com/boykopovar/AnyPS5/pull/425#issuecomment-6086182956) | — | — |
| `PPSA05324` | Sonic Origins | Presents (mined) | Linux · AMD · PR #2479 | [#2479](https://github.com/boykopovar/AnyPS5/pull/2479) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2491#issuecomment-6093034542) | — |
| `PPSA28416` | STAR WARS: Galactic Racer | Presents (mined) | Windows · PR #2888 | [#2888](https://github.com/boykopovar/AnyPS5/pull/2888) | — | — |
| `PPSA23566` | UFC 6 | Presents (mined) | Windows · NVIDIA · PR #1235 | [#1235](https://github.com/boykopovar/AnyPS5/pull/1235) | — | — |
| `PPSA29413` | Wobbly Life | Presents (mined) | Windows · NVIDIA · PR #2212 | [#2212](https://github.com/boykopovar/AnyPS5/pull/2212) | — | — |
| `PPSA99666` | DOOM | Presents (mined) | Linux · NVIDIA · main | [#1265 comment](https://github.com/boykopovar/AnyPS5/pull/1265#issuecomment-6066954325) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/690#issuecomment-6092797207) | [#1497](https://github.com/boykopovar/AnyPS5/issues/1497) |
| `PPSA28997` | God of War: Sons of Sparta | Presents (mined) | Windows · PR #1530 | [#1530](https://github.com/boykopovar/AnyPS5/pull/1530) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/593) | [#1930](https://github.com/boykopovar/AnyPS5/issues/1930) |
| `PPSA14632` | LEGO Horizon Adventures | Presents (mined) | Windows · PR #1188 | [#1188](https://github.com/boykopovar/AnyPS5/pull/1188) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/2791) | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA03671` | Marvel's Wolverine | Presents (mined) | Windows · NVIDIA · PR #197 | [#197](https://github.com/boykopovar/AnyPS5/pull/197) | — | [#1033](https://github.com/boykopovar/AnyPS5/issues/1033) |
| `PPSA01285` | Returnal | Presents (mined) | Windows · NVIDIA · main | [#2548 comment](https://github.com/boykopovar/AnyPS5/issues/2548#issuecomment-6101632487) | — | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) |
| `PPSA02100` | Stray | Presents (curated) | Windows · NVIDIA · main | [#2749](https://github.com/boykopovar/AnyPS5/issues/2749) | — | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA12544` | Hollow Knight: Silksong | Presents (mined) | Windows · NVIDIA · PR #1441 | [#1441 comment](https://github.com/boykopovar/AnyPS5/pull/1441#issuecomment-6096018875) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/904#issuecomment-6096043824) | [#865](https://github.com/boykopovar/AnyPS5/issues/865) → [#1970](https://github.com/boykopovar/AnyPS5/issues/1970) |
| `PPSA16064` | Minecraft Dungeons II | Presents (mined) | Windows · NVIDIA · PR #1118 | [#1118](https://github.com/boykopovar/AnyPS5/pull/1118) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2233) | [#2811](https://github.com/boykopovar/AnyPS5/issues/2811) → [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) |
| `PPSA30279` | Taxi Chaos 2 | Presents (curated) | Windows · NVIDIA · main + local patches | [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) | — | [#2783](https://github.com/boykopovar/AnyPS5/issues/2783) (Windows/NVIDIA) → [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) → [PR #2054](https://github.com/boykopovar/AnyPS5/pull/2054) → [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) → [PR #425](https://github.com/boykopovar/AnyPS5/pull/425) → [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) |
| `PPSA99005` | ps5-opengl showcase | First draw (curated) | Windows · NVIDIA · main + AlxcBTW#12 | [#1413 comment](https://github.com/boykopovar/AnyPS5/issues/1413#issuecomment-6095663977) | — | [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) → [#2631](https://github.com/boykopovar/AnyPS5/issues/2631) |
| `PPSA06320` | Ape Escape | Starts (mined) | Windows · PR #572 | [#572 comment](https://github.com/boykopovar/AnyPS5/pull/572#issuecomment-6045460525) | — | — |
| `PPSA21564` | Astro Bot | Starts (curated, reviewed) | Linux · NVIDIA · main de5e541d | [#2871](https://github.com/boykopovar/AnyPS5/issues/2871) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/625#issuecomment-6000352532) | — |
| `PPSA03974` | Cyberpunk's | Starts (mined) | main | [#1984 comment](https://github.com/boykopovar/AnyPS5/pull/1984#issuecomment-6074541896) | — | — |
| `PPSA34356` | Marsupilami: Hoobadventure | Starts (mined) | Windows · PR #2558 | [#2558](https://github.com/boykopovar/AnyPS5/pull/2558) | — | — |
| `PPSA17221` | Minecraft | Starts (mined) | Windows · PR #1093 | [#1093](https://github.com/boykopovar/AnyPS5/pull/1093) | — | — |
| `PPSA05510` | Minecraft Legends | Starts (mined) | main | [#1405](https://github.com/boykopovar/AnyPS5/pull/1405) | — | — |
| `PPSA01317` |  | Starts (mined) | Windows · NVIDIA · PR #2583 | [#2583](https://github.com/boykopovar/AnyPS5/pull/2583) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2589#issuecomment-6096675434) | — |
| `PPSA03747` |  | Starts (mined) | Linux · PR #1299 | [#1299 comment](https://github.com/boykopovar/AnyPS5/pull/1299#issuecomment-6051863585) | — | — |
| `PPSA15186` |  | Starts (mined) | Windows · NVIDIA · main | [#2207](https://github.com/boykopovar/AnyPS5/issues/2207) | — | — |
| `PPSA20612` | Retried | Starts (mined) | Linux · AMD · main + patches | [#2341](https://github.com/boykopovar/AnyPS5/issues/2341) | — | — |
| `PPSA99169` | RetroArch | Starts (mined) | Windows · NVIDIA · PR #757 | [#757 comment](https://github.com/boykopovar/AnyPS5/pull/757#issuecomment-6101135304) | — | — |
| `PPSA13934` | Spirit of the Island | Starts (mined) | Windows · PR #696 | [#696](https://github.com/boykopovar/AnyPS5/pull/696) | — | — |
| `PPSA05684` | Uncharted: Legacy of Thieves Collection | Starts (curated, reviewed) | main | [#2219](https://github.com/boykopovar/AnyPS5/pull/2219) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2916) | — |
| `PPSA01500` | Watch Dogs: Legion | Starts (mined) | Windows · PR #2843 | [#2843](https://github.com/boykopovar/AnyPS5/pull/2843) | — | — |
| `PPSA01341` | Demon's Souls | Starts (curated, reviewed) | Linux · main + #861 (merged) | [#2552](https://github.com/boykopovar/AnyPS5/issues/2552) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/454#issuecomment-6083716357) | [#2552](https://github.com/boykopovar/AnyPS5/issues/2552) |
| `PPSA02262` | Dying Light 2 | Starts (mined) | Windows · NVIDIA · PR #1830 | [#1830](https://github.com/boykopovar/AnyPS5/pull/1830) | — | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) |
| `PPSA99039` | EVO Player | Starts (mined) | Windows · AMD · PR #1931 | [#1931](https://github.com/boykopovar/AnyPS5/pull/1931) | — | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) |
| `PPSA07286` | Road of Death | Starts (mined) | Windows · NVIDIA · main | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) | — | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) |
| `PPSA03001` | Sifu | Starts (mined) | Windows · NVIDIA · main | [#1409 comment](https://github.com/boykopovar/AnyPS5/issues/1409#issuecomment-6097394354) | — | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) |
| `PPSA01325` | Astro's Playroom | Starts (curated, reviewed) | Windows · NVIDIA · main | [#2156](https://github.com/boykopovar/AnyPS5/pull/2156) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/2085#issuecomment-6080996572) | [#2476](https://github.com/boykopovar/AnyPS5/issues/2476) → [#2914](https://github.com/boykopovar/AnyPS5/issues/2914) |
| `PPSA02530` | PRAGMATA | Starts (mined) | Windows · PR #369 | [#369](https://github.com/boykopovar/AnyPS5/pull/369) | — | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) → [#3043](https://github.com/boykopovar/AnyPS5/issues/3043) |
| `PPSA01474` | Ratchet & Clank: Rift Apart | Starts (mined) | Linux · AMD · main + patches | [#2102 comment](https://github.com/boykopovar/AnyPS5/issues/2102#issuecomment-6080943741) | — | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) |
| `PPSA07411` | Resident Evil 4 | Starts (mined) | Windows · main + patches | [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) | — | [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) → [#2776](https://github.com/boykopovar/AnyPS5/issues/2776) |
| `PPSA33286` | Silent Hill: Townfall | Starts (mined) | Windows · NVIDIA · main | [#2102 comment](https://github.com/boykopovar/AnyPS5/issues/2102#issuecomment-6081268754) | — | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2747](https://github.com/boykopovar/AnyPS5/issues/2747) |
| `PPSA21567` | Astro Bot | Starts (mined) | Windows · PR #2817 | [#2817](https://github.com/boykopovar/AnyPS5/pull/2817) | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/425#issuecomment-6060747884) | [#665](https://github.com/boykopovar/AnyPS5/issues/665) → [#479](https://github.com/boykopovar/AnyPS5/issues/479) → [#2775](https://github.com/boykopovar/AnyPS5/issues/2775) |
| `PPSA15657` | Disney Epic Mickey: Rebrushed | Starts (mined) | Linux · AMD · main | [#2366](https://github.com/boykopovar/AnyPS5/issues/2366) | Menus, [source](https://github.com/boykopovar/AnyPS5/issues/2365) | [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) → [#2365](https://github.com/boykopovar/AnyPS5/issues/2365) → [#2366](https://github.com/boykopovar/AnyPS5/issues/2366) |
| `PPSA26344` | Ghost of Yōtei | Starts (curated, reviewed) | main | [#1920](https://github.com/boykopovar/AnyPS5/issues/1920) | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/757#issuecomment-6080729041) | [#2715](https://github.com/boykopovar/AnyPS5/issues/2715) → [#1920](https://github.com/boykopovar/AnyPS5/issues/1920) → [#2355](https://github.com/boykopovar/AnyPS5/issues/2355) |
| `PPSA99902` | Sonic Unleashed Recompiled | Starts (mined) | Windows · NVIDIA · main + patches | [#3037](https://github.com/boykopovar/AnyPS5/issues/3037) | — | [#2886](https://github.com/boykopovar/AnyPS5/issues/2886) → [#2970](https://github.com/boykopovar/AnyPS5/issues/2970) → [#3036](https://github.com/boykopovar/AnyPS5/issues/3036) → [#3037](https://github.com/boykopovar/AnyPS5/issues/3037) |
| `PPSA03647` | 3D MiniGolf | Converts (mined) | Windows · PR #1849 | [#1849](https://github.com/boykopovar/AnyPS5/pull/1849) | — | — |
| `PPSA99600` | Cloud Play | Converts (mined) | Windows · main | [#2525 comment](https://github.com/boykopovar/AnyPS5/issues/2525#issuecomment-6095102807) | — | — |
| `PPSA99997` | Nuvio PS5 | Converts (mined) | Windows · PR #2186 | [#2186 comment](https://github.com/boykopovar/AnyPS5/pull/2186#issuecomment-6092621656) | — | — |
| `PPSA99082` | OpenNOW | Converts (mined) | Windows · main | [#1578 comment](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) | — | — |
| `PPSA99728` | OpenRCT2 Native Port | Converts (mined) | Windows · PR #2933 | [#2933](https://github.com/boykopovar/AnyPS5/pull/2933) | — | — |
| `PPSA99808` | PICO-8 for PS5 | Converts (mined) | Windows · PR #2107 | [#2107](https://github.com/boykopovar/AnyPS5/pull/2107) | — | — |
| `PPSA99764` | Porpoise | Converts (mined) | Linux · PR #2231 | [#2231 comment](https://github.com/boykopovar/AnyPS5/pull/2231#issuecomment-6081524924) | — | — |
| `PPSA13427` |  | Converts (mined) | Linux · NVIDIA · PR #1481 | [#1481](https://github.com/boykopovar/AnyPS5/pull/1481) | — | — |
| `PPSA99010` |  | Converts (mined) | Windows · NVIDIA · PR #1627 | [#1627 comment](https://github.com/boykopovar/AnyPS5/pull/1627#issuecomment-6072368118) | — | — |
| `PPSA99995` | Prospero Win | Converts (mined) | Windows · PR #3050 | [#3050](https://github.com/boykopovar/AnyPS5/pull/3050) | — | — |
| `PPSA99177` | PS5VR | Converts (mined) | Linux · PR #1714 | [#1714 comment](https://github.com/boykopovar/AnyPS5/pull/1714#issuecomment-6080529330) | — | — |
| `PPSA99810` | PSBox Cloud Gaming | Converts (mined) | Windows · PR #2186 | [#2186 comment](https://github.com/boykopovar/AnyPS5/pull/2186#issuecomment-6092621656) | — | — |
| `PPSA76677` | RommPS | Converts (mined) | Windows · PR #1871 | [#1871 comment](https://github.com/boykopovar/AnyPS5/pull/1871#issuecomment-6093920746) | — | — |
| `PPSA69420` | ScreenTester5 | Converts (mined) | Windows · PR #1872 | [#1872 comment](https://github.com/boykopovar/AnyPS5/pull/1872#issuecomment-6093920638) | — | — |
| `PPSA03306` | Silt | Converts (mined) | Windows · NVIDIA · PR #1196 | [#1196 comment](https://github.com/boykopovar/AnyPS5/pull/1196#issuecomment-6045207508) | — | — |
| `PPSA21607` | Smurfs Dreams | Converts (mined) | Windows · PR #911 | [#911](https://github.com/boykopovar/AnyPS5/pull/911) | — | — |
| `PPSA74126` | Stremio Plus | Converts (mined) | Windows · PR #2934 | [#2934](https://github.com/boykopovar/AnyPS5/pull/2934) | — | — |
| `PPSA98510` | SwanStationPS5 | Converts (mined) | Windows · PR #2186 | [#2186 comment](https://github.com/boykopovar/AnyPS5/pull/2186#issuecomment-6092621656) | — | — |
| `PPSA25344` | Sword of the Sea | Converts (mined) | Windows · PR #2412 | [#2412](https://github.com/boykopovar/AnyPS5/pull/2412) | — | — |
| `PPSA97358` | XPSemu | Converts (mined) | Windows · PR #3056 | [#3056](https://github.com/boykopovar/AnyPS5/pull/3056) | — | — |
| `PPSA92280` | Capy Mobile | Converts (mined) | Windows · NVIDIA · PR #1634 | [#1634 comment](https://github.com/boykopovar/AnyPS5/pull/1634#issuecomment-6072368292) | — | [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) |
| `PPSA06465` | Cult of the Lamb | Converts (mined) | Windows · main + patches | [#2686](https://github.com/boykopovar/AnyPS5/issues/2686) | — | [#2686](https://github.com/boykopovar/AnyPS5/issues/2686) |
| `PPSA99515` | Emby5 | Converts (mined) | Linux · main | [#2764 comment](https://github.com/boykopovar/AnyPS5/pull/2764#issuecomment-6100887532) | — | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) |
| `PPSA03355` | Hades | Converts (mined) | Windows · PR #1798 | [#1798](https://github.com/boykopovar/AnyPS5/pull/1798) | — | [#2724](https://github.com/boykopovar/AnyPS5/issues/2724) |
| `PPSA99505` | Jelly5 | Converts (mined) | Linux · main | [#2764 comment](https://github.com/boykopovar/AnyPS5/pull/2764#issuecomment-6100887532) | — | [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) |
| `PPSA28319` | Middle Ages Ping Pong | Converts (mined) | Windows · NVIDIA · main | [#2942 comment](https://github.com/boykopovar/AnyPS5/issues/2942#issuecomment-6101892072) | — | [#2942](https://github.com/boykopovar/AnyPS5/issues/2942) |
| `PPSA99110` | Prospero Multi Tools | Converts (mined) | Windows · PR #1633 | [#1633 comment](https://github.com/boykopovar/AnyPS5/pull/1633#issuecomment-6072451462) | — | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA99009` | ProsperoLichess | Converts (mined) | Windows · main | [#1578 comment](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6091750552) | — | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) |
| `PPSA99002` | ProsperoLight | Converts (mined) | Windows · main | [#1578 comment](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6091750552) | — | [PR #1482](https://github.com/boykopovar/AnyPS5/pull/1482) |
| `PPSA99001` | ProsperoRadio | Converts (mined) | Windows · main | [#1578](https://github.com/boykopovar/AnyPS5/issues/1578) | — | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) |
| `PPSA99000` | ProsperoStore | Converts (mined) | Windows · main | [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) | — | [#2908](https://github.com/boykopovar/AnyPS5/issues/2908) |
| `PPSA99003` | ProsperoTV | Converts (mined) | Windows · main | [#1637 comment](https://github.com/boykopovar/AnyPS5/pull/1637#issuecomment-6099914155) | — | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) |
| `PPSA97510` | PSXS5 | Converts (mined) | Windows · PR #2186 | [#2186 comment](https://github.com/boykopovar/AnyPS5/pull/2186#issuecomment-6092621656) | — | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578) |
| `PPSA68091` | Ruffle Flash | Converts (mined) | Windows · main | [#1578 comment](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) | — | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA19111` | XashPS5 | Converts (mined) | Windows · main | [#1578 comment](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) | — | [row in #1578](https://github.com/boykopovar/AnyPS5/issues/1578#issuecomment-6092658382) |
| `PPSA99007` | Yamagi Quake II | Converts (mined) | Windows · main | [#2106 comment](https://github.com/boykopovar/AnyPS5/pull/2106#issuecomment-6095055479) | — | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA15508` | Last of Us Part II Remastered | Converts (mined) | Windows · NVIDIA · main | [#2830](https://github.com/boykopovar/AnyPS5/pull/2830) | — | [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) → [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) |
| `PPSA23126` | Palworld | Converts (mined) | Windows · main + patches | [#2648](https://github.com/boykopovar/AnyPS5/issues/2648) | — | [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) → [#2648](https://github.com/boykopovar/AnyPS5/issues/2648) |
| `PPSA11386` | 007 First Light | Converts (mined) | Windows · NVIDIA · main | [#2830](https://github.com/boykopovar/AnyPS5/pull/2830) | — | [PR #2471](https://github.com/boykopovar/AnyPS5/pull/2471) → [#2523](https://github.com/boykopovar/AnyPS5/issues/2523) → [#2642](https://github.com/boykopovar/AnyPS5/issues/2642) → [#2774](https://github.com/boykopovar/AnyPS5/issues/2774) |
| `PPSA03748` | Kerbal Space Program | — |  | — | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/1985#issuecomment-6074542370) | — |
| `PPSA03524` |  | — |  | — | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/1196#pullrequestreview-5447519171) | — |
| `PPSA10600` | Ad Infinitum | — |  | — | — | [#3043](https://github.com/boykopovar/AnyPS5/issues/3043) |
| `PPSA04029` | Cyberpunk 2077 | — |  | — | — | [#3032](https://github.com/boykopovar/AnyPS5/issues/3032) |
| `PPSA01521` | Horizon Forbidden West | — |  | — | Menus, [source](https://github.com/boykopovar/AnyPS5/pull/1269#issuecomment-6067762406) | [#2809](https://github.com/boykopovar/AnyPS5/issues/2809) |
| `PPSA01746` | Kena: Bridge of Spirits | — |  | — | — | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA01802` | Kena: Bridge of Spirits | — |  | — | — | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA10261` | Lies of P | — |  | — | — | [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) |
| `PPSA99109` | Prospero Explorer | — |  | — | — | [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) |
| `PPSA28502` | Pure Pool Pro | — |  | — | Ingame, [source](https://github.com/boykopovar/AnyPS5/pull/1390#issuecomment-6088757108) | [#1455](https://github.com/boykopovar/AnyPS5/issues/1455) |
| `PPSA04540` | Rise of the Ronin | — |  | — | — | [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) |
| `PPSA10112` | Silent Hill: The Short Message | — |  | — | — | [#1409](https://github.com/boykopovar/AnyPS5/issues/1409) |

## Coverage

- RDNA ISA decode: 1166 of 1166 (100.0%)
- HLE functions: 2718 of 3219 (84.44%)
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
- `libkernel`: `__tls_get_addr_nid_postfix` (#2476)
- `libkernel`: `pthread_attr_setsolosched_np_nid_postfix` (#1967, #2598)
- `libkernel`: `sceCoredumpAttachMemoryRegionAsUserFile` (#2598)
- `libkernel`: `sceCoredumpAttachUserFile` (#2598)
- `libkernel`: `sceCoredumpSetUserDataType` (#1967, #2598)
- `libkernel`: `sceCoredumpWriteUserData` (#1578, #1967, #2523, #2598)
- `libkernel`: `sceCoredumpWriteUserString` (#1967, #2598)
- `libkernel`: `sceKernelFcntl` (#3048)
- `libkernel`: `sceKernelInternalMemoryGetModuleSegmentInfo_nid_postfix` (#2476)
- `libkernel`: `sceKernelRaiseException` (#1, #693, #1471, #1488)

## Help wanted

- [#2548](https://github.com/boykopovar/AnyPS5/issues/2548) Packed pixel ancillary word read whole after its VGPR is reused: Test AlxcBTW/AnyPS5#25 on Stray, LEGO Horizon, Kena and Lies of P and report which shaders still fail.
- [PR #2106](https://github.com/boykopovar/AnyPS5/pull/2106) pthread_sigmask is not exported (libkernel): Needs an author who passes the PR intake rule, or a maintainer to reopen #2106.
- [#2591](https://github.com/boykopovar/AnyPS5/issues/2591) Road of Death (PPSA07286) fails on startup: missing libSceXml.prx: First open blocker for 4 titles; no open fix PR
- [PR #1872](https://github.com/boykopovar/AnyPS5/pull/1872) pthread_set_name_np is not exported (libkernel): First open blocker for 2 titles; no open fix PR
- [#2102](https://github.com/boykopovar/AnyPS5/issues/2102) Layered rendering: color views of several array slices: First open blocker for 3 titles; no open fix PR
- [#1413](https://github.com/boykopovar/AnyPS5/issues/1413) v_interp_mov P10/P20 of a flat input without pass-through: Hardware answer needed (tools/hw-oracle on a PS5-class GPU).
- [#1794](https://github.com/boykopovar/AnyPS5/issues/1794) Dying Light 2 (PPSA02262) on Windows: what stops it between conversion and its own startup: First open blocker for 2 titles; no open fix PR
- [#3043](https://github.com/boykopovar/AnyPS5/issues/3043) PRAGMATA (PPSA02530 v01.200.000) on Windows: the title's libc rejects its allocator's mspace buffer in the ASLR-relocated image above 1 TiB, so the first malloc returns NULL and start-up faults: First open blocker for 1 title; no open fix PR
- [#2701](https://github.com/boykopovar/AnyPS5/issues/2701) libkernel: support kern.sdk_version in sysctlbyname (Capy Mobile PPSA92280): First open blocker for 1 title; no open fix PR
- [#2621](https://github.com/boykopovar/AnyPS5/issues/2621) Ratchet & Clank: Rift Apart: a registered pixel shader is drawn with DB_SHADER_CONTROL=0 while its header sets 0x20601: First open blocker for 1 title; no open fix PR
- [#3055](https://github.com/boykopovar/AnyPS5/issues/3055) AGC: GTA V libSceJobManager compute kernel reads its V#s from a block that is still all 0xFF at capture: First open blocker for 1 title; no open fix PR
- [#2942](https://github.com/boykopovar/AnyPS5/issues/2942) Launching Silksong Failed: First open blocker for 1 title; no open fix PR

## Known gaps

- Title names, engines and stages are mined with keyword rules per line; negation and context are handled only roughly.
- Mined chain order is a heuristic: the latest recorded stop first, then issues by creation date.
- Read: issue and PR bodies, their comments, PR reviews and review-thread comments (up to 100 threads and 50 comments per thread), and timeline cross-references. Not read: commit messages, diffs, attached logs and screenshots (images, gists, uploaded files), edit history, and bot comments.
- Issues and PRs closed more than 60 days ago are not read, even when they hold the last report on a title.
- Stops are read from a fenced log only when the comment names exactly one title ID; the last error line in the block counts as the stop.
- “N reports on main” counts distinct GitHub accounts whose text puts the title at that stage on main. It cannot tell whether two accounts tested the same build, and text without a stated build counts as main in issues and as the PR branch in PRs.
- Titles without a PPSA ID (some homebrew) appear only when curated.
- Discord reports are invisible unless someone copies them into GitHub or the curated file.
- Signatures are matched by prefix after hex addresses and long numbers are masked; reworded messages split into separate keys.
- PM4 status reads Pm4::UnsupportedReason(); a packet can pass that check and still be emulated partially.
- Stages mined from PR text describe the PR branch (build “PR #N”), not main, unless the sentence says main and names no patches.
- An issue that names seven or more titles is treated as a tracker: only its per-title stop rows count, as separate blockers.
- HLE “named in issues” counts any mention of a missing function, including lists of imports that were never reached.
- A mined stage of Menus or higher is only a claim until a person reviews it; most such claims in PR text were made on branches with open PRs.

