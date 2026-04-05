#!/bin/bash

# update -b with working cookie from browser dev-tools

curl 'https://custodian.vklass.se/Events/FullCalendar' \
  -H 'accept: */*' \
  -H 'accept-language: sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6' \
  -H 'content-type: application/x-www-form-urlencoded' \
  -b 'se.vklass.authentication=CfDJ8AF1v64zmWNJt9xTu8U9aMopg3PTtAP5f1brjGKyLtrpzhr0ZiFKcw5UqQkJ-u4qnKWqdt-peyCqushSXI_O7mqGj_xxir-me0pu_f97KL14sM4eIaGiVcZIziK5-oJfoM4uwN3voiCNAA_hqb4meqc77b_n7lTFNPPC_Ij3VMT0fnxmh6LZFvo1J5RFX2C2mMg7FLJk2cZzlab0SRK7sySdHTwMzyL_wVfN9dp54D6nQCmJbMpIWyg9kBF9_vCqv_JwxJOzGOv5mVonhLHSAUXWSNBYREvRwzCN53TNN5uIJOcsDbqZDm0wG28HQNSgVhvLYv1YVOpmEamd3E9OjbrvhVLUKtgKpx21rgOwqoGrab3hiJh5tL7WaY5S66GNMsZeyg1Ep4pChTD6Z3DLWO6XL8444hNB4T3_fnxhDFEdrsWtvW6yEnMpFb7E_lzlz_bP9dYb_Vv10DRFlUapR0c1oKIIhDn_FN0DwL78vorIifCFpslyfNgV8rQPQFJMbNKhVbBzNlzBiF5jwzMhedRTgvHtoITAPE7ih-H7FgrPKiaT-9B1Hw4JN7M8MeJ22inEYz5zt_XadcEYyjQqbCKuhLhSc13XugeGK_cZhT-uHcb24UgocHzNh4A8rAjU-cPqM_y_vddwjACPZqgQO_if8AETCUIN_GPkkWiAQgnWaqAV9b4s8m-4Kjm0GWaOzt5RnZWyZ1KQUm2P7RLCRMAlAL_3JC0EqcQbbpQ5Kiw2OEJyy8M41SBaSNaYRFBJI1w5W32X8w0sjkLrIVYMUI_v7ggjSFMxr9et6f96ySoncSQEQ21C0btpwvckrMQYcF8oeacZtXVo_Yap685UTv9HVGKUkLRYu_B5dWs7F7XtZ9advuNt6vDNTl2E1hihmrjCb8YimGnYWo_oOlPjHCr4p8Lk_GCNsYTLzkkL_8pYDh7kCA6CknW5x0W1HAQkbgn-fpQNhVBO0sQu1qwnFKm0yFSUOyCC3BHw4jSmmSgzVXHwklRFs5cqTq36RdisaZJUWiBfeEtY08zEtHt--k5VBpiCfbq0UL66J9nYvTXIJhZPvnsOJHU224WNszmmgOpc3spzPFyvdkCIt8sWCSyQJFT42x6l9czotmQ4LfsBk2uV_dTm44A1PUpPZDuMYHUN6bHseHSmNGmId3UIx7bom8csXp6yqXW6981HQHDHzM3CF-N-kEMN8_LaTn1XH3lNQaB7vIYi6FvEohLItbOIvoEfIz3TAlxGV--4SQlojGHoaO-dBTTQsDDVlU78sCoimgEyBZkbSKtFbfb5aZ8LTkd1Ga99PM4Wny7IMxlWlZHzIzTaspCgi3eYii1qFz-Q4euHyhXM1whoizSsWrFtFk59-cmyU6h3A--dKmfs-fpabCsMXr52ZVIjA9L8BemRzaRY1BB97B3bFTxHaCPONsAJxpUrXsRc4faKwXt4X2qwtTkt6YA1Wquv0AxPMDPH67oCGJV2Fp75CnwFMChaMDGgTbvPQk8VImdrIPUMVTkxU7kot4qCNGTEzB9k7mDCSzcT5NCsRkEqwj3EmVvS9-bqoNBzegJxSFPCt1jaiPrdkHKkfaAmDy9P2RPk2DG6euCMlCT84ulYaos_jKY; LogoutRedirectURL=%2Fsaml%2Fsignout; vhvklass.ASPXAUTH=E482C0B57DF9419D7FA44A65897026EDCC29AF5C4876330440C4CD04A2DC7E9E5C3D140D4FF30755788764D414BD53B6372BBDE8989730114F2C1473C091FF2335B003543C1AFB139715A019AB7B83177293B45AA466A2BA728177E3FF570995840A38AB9BD509E376B380CD77463CF993CCC74DE5C7132C2BCED7E0F39DBB969323218C; vk.vh.localization=c%3Dsv-SE%7Cuic%3Dsv-SE; .AspNetCore.Antiforgery.ozsKLpGWkJs=CfDJ8AF1v64zmWNJt9xTu8U9aMo6HgPLmXaO-1HThHupLsg1nuolOwTFiReLADfOM7Qn0LxYXgia3cOZIGhIc3xAjOVD-JC6Bn-7vVZ5VkjkoyUKwa0-V99LMwtJIRQi9iN6RscZcFqDIBG88ZoQZDDKAVU; vk-pointer=mouse' \
  -H 'dnt: 1' \
  -H 'origin: https://custodian.vklass.se' \
  -H 'priority: u=1, i' \
  -H 'referer: https://custodian.vklass.se/' \
  -H 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36' \
  --data-raw 'students=974364%2C1223735&start=2026-03-23T00%3A00%3A00%2B01%3A00&end=2026-03-28T00%3A00%3A00%2B01%3A00'