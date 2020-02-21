m8_base: equ 0x0401

main:
    ld hl, 0x0e0f
    ld hl, m8_base
    ld b, 0xaf
    inc hl
    dec b
    jp z, m8_bff_full
    jp m8_bff_next
    ld a, 0xff
    sub b
    ld h, 0x00
    ld l, a
    ret
