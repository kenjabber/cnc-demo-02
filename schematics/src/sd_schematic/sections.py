"""Transcribed section netlists for Servo Dynamics SD1015/SD1525, dwg 1202 sheet 2 (PDF p.30).
Each section was read independently from a 400 dpi crop of the scan."""
SECTIONS = {}

SECTIONS["S1_input"] = {
 "parts":[
  ("J1","CONN",["1","2","3","4","5"]),("J2","CONN",["1","2"]),
  ("U1A","OPAMP",["1","2","3"]),("U1B","OPAMP",["4","5","6","7","8"]),
  ("JMP1","JUMPER",["A","B","W"]),
  ("R1","R",None),("R2","R",None),("R3","R",None),("R4","R",None),("R5","R",None),
  ("R6","R",None),("R7","R",None),("R8","R",None),("R9","R",None),("R10","R",None),
  ("R11","R",None),("R27","POT",None),("R28","POT",None),("R29","POT",None),
  ("R33","R",None),("R34","R",None),("R35","R",None),("R36","R",None),("R37","R",None),
  ("R57","R",None),("R58","R",None),("R59B","R",None),
  ("C1","C",None),("C2","C",None),("C3","C",None),("C4","C",None),("C5","C",None),
  ("C6","CPOL",None),("C7","CPOL",None),("C8","CPOL",None),("C9","CPOL",None),
  ("C16","C",None),("C17","C",None),
  ("TP1","TP",["1"]),("TP2","TP",["1"]),("TP3","TP",["1"]),("TP4","TP",["1"]),("TP6","TP",["1"]),
 ],
 "nets":[
  ("N_J2_1",["J2.1","R1.1"]),
  ("N_IN1",["R1.2","C2.1","R3.1"]),
  ("N_U1A_INV",["R3.2","U1A.2","R2.1"]),
  ("N_J2_2",["J2.2","R4.1"]),
  ("N_IN2",["R4.2","C3.1","R5.1"]),
  ("N_U1A_NONINV",["R5.2","U1A.3","R6.1"]),
  ("N_DIFFOUT",["U1A.1","R2.2","JMP1.B"]),
  ("N_J1_1",["J1.1","R7.1"]),
  ("N_AUX_IN",["R7.2","C4.1","R27.1"]),
  ("N_J1_2",["J1.2","R8.1"]),
  ("N_JMP_A",["R8.2","C5.1","JMP1.A"]),
  ("N_SIGTOP",["JMP1.W","R28.1"]),
  ("N_SIG",["R28.2","TP3.1","R34.1"]),
  ("N_AUX",["R27.2","TP2.1","R33.1"]),
  ("N_J1_3_TACH_IN",["J1.3","TP6.1","R9.1"]),
  ("N_T1A",["R9.2","C6.1","R10.1"]),
  ("N_C6_C7_MID",["C6.2","C7.1"]),
  ("N_T2A",["R10.2","C1.1","R11.1"]),
  ("N_TACH",["R11.2","C17.1","R29.1","C16.1"]),
  ("N_CT",["C16.2","R35.1"]),
  ("N_TACH_W",["R29.2","TP4.1","R37.1"]),
  ("N_SUM",["R34.2","R33.2","R35.2","R37.2","U1B.6","R57.1"]),
  ("N_BAL_INJ",["R57.2","R58.1","R59B.1"]),
  ("P15",["U1B.8","C9.1"]),
  # AUDIT: C8 was transcribed here with its plates the other way round -
  # C8.1 on N15 and C8.2 on GND - while S4_comp reads C8.1 on GND and C8.2 on
  # N15. Since the two sections share both pins, the merge tied N15 and GND
  # into one node and the whole -15 V rail (17 pins) vanished into GND.
  # S4_comp is the correct reading: C8 is drawn with its "+" on the grounded
  # plate, which is right for a decoupler on a negative rail, and pin 1 is the
  # "+" plate. Corrected here to match.
  ("N15",["U1B.4","C8.2"]),
  ("CHASSIS",["R36.2"]),
  ("GND",["C2.2","C3.2","R6.2","C4.2","C5.2","R28.3","R27.3","R29.3","U1B.5","C9.2",
          "C8.1","R58.2","R59B.2","J1.4","C7.2","C1.2","C17.2","TP1.1","R36.1"]),
 ],
}

SECTIONS["S2_avamp"] = {
 "parts":[
  ("R16","R",None),("U2A","OPAMP",["1","2","3"]),("U2B","OPAMP",["12","13","14"]),
  ("U2C","OPAMP",["8","9","10"]),("R13","R",None),("R15","R",None),("R14","R",None),
  ("D9","ZENER",None),("R42","R",None),("R43","R",None),("D12","D",None),("D13","D",None),
  ("D12A","ZENER",None),("RMSTIMER","BLOCK",["1","2","3"]),("R19","R",None),("R44","POT",None),
  ("R21","R",None),("R20","R",None),("U3","COMP",["10","11","13"]),("TP8","TP",["1","2"]),
  ("C10","C",None),("C11","C",None),("C12","C",None),
  ("D1","D",None),("D2","D",None),("D3","D",None),
  ("R50","R",None),("R45","R",None),("R67","R",None),("D14","D",None),
 ],
 "nets":[
  ("N_J1_5_IN",["R16.1","J1.5"]),
  ("N_U2A_OUT",["R16.2","U2A.1","U2A.2"]),
  ("N_AV_BUF_IN",["U2A.3","R14.2","D9.2"]),
  ("N_AV_OUT",["U2B.14","R15.2","R14.1","R42.2","D12.1"]),
  ("N_U2B_INV",["U2B.13","R15.1","R13.1"]),
  ("N_ECC_FB",["R13.2","R91.2"]),
  ("N_U2C_INV",["U2C.9","R42.1","R43.1"]),
  ("N_U2C_OUT",["U2C.8","R43.2","D13.1"]),
  ("N_RECT_OUT",["D12.2","D13.2","D9.1","RMSTIMER.1"]),
  ("N_D12A_TOP",["D12A.2"]),   # AUDIT: exits right at sheet y~1398, destination unresolved
  ("N_RMS_TOP",["D12A.1","RMSTIMER.2"]),
  ("N_RMS_OUT",["RMSTIMER.3","R19.1"]),
  ("N_RMS_LEVEL",["R19.2","R44.1","R44.2"]),
  ("P100",["R21.1"]),
  ("N_U3_INV",["R21.2","R20.1","U3.11","TP8.1"]),
  ("N_U3_OUT",["U3.13","R50.2","R47.1","R46.1"]),
  ("N_J1_6",["D1.2","C10.1","J1.6"]),
  ("N_J1_7",["D2.2","C11.1","J1.7"]),
  ("N_J1_8",["D3.2","C12.1","J1.8"]),
  ("N_R47_BOT",["R47.2","D1.1","R48.1","D11.1"]),
  ("N_R46_BOT",["R46.2","R45.1","D2.1","D10.1"]),
  ("N_CLAMP",["D3.1","D10.2","D11.2","R49.2","Q2.C"]),
  ("N_U4A_BASE",["R45.2","U4A.13"]),
  ("N_U4A_COL",["U4A.12","R64B.2","R65.1"]),
  ("N_R67_D14",["R67.2","D14.1","J1.14"]),
  ("P15",["R50.1","R67.1","TP8.2"]),
  ("N15",["R20.2"]),
  ("GND",["U2B.12","U2C.10","U3.10","C10.2","C11.2","C12.2","R44.3"]),
 ],
}

SECTIONS["S3_basedrive"] = {
 "parts":[
  ("J1","CONN",["7","8","9","10","11","12","13","14","15"]),
  ("R59","R",None),("R60","R",None),("R46","R",None),("R47","R",None),("R48","R",None),
  ("D10","ZENER",None),("D11","ZENER",None),("D17","D",None),
  ("R64A","R",None),("R80A","R",None),("R64B","R",None),("R65","R",None),("R66","R",None),
  ("R80B","R",None),("R81","R",None),("R82","R",None),("R83","R",None),
  ("R49","R",None),("R68","R",None),("R69","R",None),("Q2","NPN",["B","C","E"]),
  ("U4A","NPN",["12","13","14"]),("U4B","NPN",["1","2","3"]),
  ("U4C","NPN",["8","9","10"]),("U4D","NPN",["5","6","7"]),
 ],
 "nets":[
  ("GND",["J1.9","J1.11","R59.2","R60.2","R65.2","R66.2","R68.2","R81.2","R82.2",
          "Q2.E","U4B.3","U4D.5"]),
  ("P15",["J1.10","R49.1","R64B.1","R80B.1","R83.1"]),
  ("N15",["J1.12"]),
  ("N_J1_13",["J1.13","N_LOCKOUT_INH1"]),
  ("N_J1_14",["J1.14","R59.1"]),
  ("N_J1_15",["J1.15","R60.1","R83.2","D17.1"]),
  ("N_DRVA",["D14.2","U4A.14","R66.1","U4B.2","R64A.2"]),
  ("N_DRVC",["D17.2","U4C.8","R82.1","U4D.6","R80A.2"]),
  ("N_R47_TOP",["R47.1","R46.1","R50.2","U3.13"]),
  ("N_U4C_BASE",["U4C.9","R48.2"]),
  ("N_U4C_COL",["U4C.10","R80B.2","R81.1"]),
  ("N_U4B_COL",["U4B.1","N_LOCKOUT_INH2"]),
  ("N_U4D_COL",["U4D.7","N_LOCKOUT_INH3"]),
  ("N_Q2_BASE",["Q2.B","R69.2","R68.1"]),
  # AUDIT: neither of these reaches the ECC node - x=1510 and x=1679 verticals cross
  # the y=2432 bus with no dot / with hops. Upper destinations unresolved.
  ("N_R69_TOP",["R69.1"]),
  ("N_R64A_R80A_TOP",["R64A.1","R80A.1"]),
 ],
}

SECTIONS["S4_comp"] = {
 "parts":[
  ("J3","CONN",["1","2","3","4"]),
  ("R113","R",None),("R56","R",None),("C18","C",None),("R53","R",None),("R52","R",None),
  ("R51","R",None),("R54","R",None),("R30","POT",None),("TP5","TP",["1"]),
  ("R39","R",None),("R38","R",None),("D5","D",None),("D6","D",None),("D7","D",None),("D8","D",None),
  ("R12A","R",None),("R12B","POT",None),("R31","POT",None),
  ("Q1","JFET",["D","G","S"]),("R41","R",None),("R40","R",None),
  ("R78A","R",None),("R60B","R",None),("R32","POT",None),("R79","R",None),
  ("D15","D",None),("D16","D",None),
 ],
 "nets":[
  ("N_SUM",["J3.4","R113.1","R56.1","R53.1","R57.1","U1B.6"]),
  ("N_J3_2",["J3.2","R113.2"]),
  ("N_RA_CA",["R56.2","C18.1"]),
  ("N_COMP_W",["C18.2","R30.2","TP5.1"]),
  ("N_R30_TOP",["R30.1","R51.1"]),
  ("N_FB_DIV",["R53.2","R52.1","R54.1"]),
  ("N_U1B_OUT",["U1B.7","D5.2","D6.1"]),
  ("N_CLAMP_TOP",["R39.2","D5.1","D7.1"]),
  ("N_CLAMP_BOT",["R38.1","D6.2","D8.2"]),
  ("N_CL",["D7.2","D8.1","R52.2","R30.3","R12A.1","R31.1","R31.2","J3.1","R40.2"]),
  ("N_PEAK_I",["R12A.2","R12B.1","R12B.2"]),
  ("N_ILIM_BOT",["R31.3","R35B.1"]),
  ("N_Q1_G",["Q1.G","R41.2"]),
  ("N_Q1_D",["Q1.D","R40.1"]),
  ("N_ECC",["R41.1","U9B.7"]),   # AUDIT-VERIFIED: R41 left -> down x1450 -> right y1480 -> down x1743 -> U9 pin 7
  ("N_BAL_INJ",["R57.2","R58.1","R59B.1","R60B.1"]),
  ("N_BAL_W",["R60B.2","R32.2"]),
  ("N_BAL_P",["R78A.2","R32.1","D15.1"]),
  ("N_BAL_N",["R79.2","R32.3","D16.2"]),
  ("P15",["R39.1","U1B.8","C9.1","R78A.1"]),
  ("N15",["R38.2","U1B.4","C8.2","R79.1"]),
  ("GND",["J3.3","R51.2","R54.2","U1B.5","C9.2","C8.1","R12B.3","R35B.2","Q1.S",
          "R58.2","R59B.2","D15.2","D16.1"]),
 ],
}

SECTIONS["S5_supply"] = {
 "parts":[
  ("R124","R",None),("R125","R",None),("R120","R",None),("R121","R",None),
  ("R122","R",None),("R126","R",None),("R118","POT",None),("R119","POT",None),
  ("C30","C",None),("C31","C",None),("D44","ZENER",None),
  ("U8A","OPAMP",["1","2","3"]),("U8B","OPAMP",["4","5","6","7","8"]),
  ("R86","R",None),("D18","D",None),("R100","R",None),("R123","R",None),
  ("R87","R",None),("R99","R",None),("D24","D",None),
  ("U7A","IC",["12","13","14","7"]),("U7D","IC",["10","11"]),
  ("J4","CONN",["1","2","3"]),("C42","CPOL",None),("C50","CPOL",None),
 ],
 "nets":[
  ("P100",["R124.1","R21.1"]),
  ("N_R124_R125",["R124.2","R125.1"]),
  ("N_BUSSENSE",["R125.2","R120.1","C30.1","U8A.2"]),
  ("N_HIBUSADJ",["R120.2","R118.1"]),
  ("N_15VSENSE",["R121.2","R122.1","C31.1","U8B.6"]),
  ("N_15VADJ",["R122.2","R119.1"]),
  ("N_ZREF",["R126.2","C30.2","U8A.3","C31.2","U8B.5","D44.2"]),
  ("N_U8A_OUT",["U8A.1","R86.1"]),
  ("N_OVERVOLT",["R86.2","D18.1","C20.2","U6.15"]),
  ("N_U8B_OUT",["U8B.7","R123.1","R100.1"]),
  ("N_U7A_IN",["R100.2","U7A.13"]),
  ("N_U7A_OUT",["U7A.12","D18.2"]),
  ("N_TO_SURGE_DET",["U7D.11","R87.1","SURGE_DETECTOR.OUT"]),
  ("N_U7D_OUT",["U7D.10","R99.1","D24.1"]),
  ("N_U6_7",["R99.2","D24.2","U6.7","C27.1"]),
  ("N_U6_PIN3",["R84.2","C21.2","R85.2","U6.3"]),
  ("BUSCOM",["R85.1"]),
  ("P15",["J4.1","C50.1","U8B.8","U7A.14","R121.1","R126.1","R84.1","C20.1","U6.16","U6.5"]),
  ("N15",["J4.3","C42.2","U8B.4","R87.2","R118.2","R118.3","R119.2","R119.3","D44.1"]),
  ("GND",["J4.2","C42.1","C50.2","U7A.7","C21.1"]),
 ],
}

SECTIONS["S6_fault"] = {
 "parts":[
  ("U6","IC",["1","3","4","5","6","7","8","9","10","11","12","13","14","15","16"]),
  ("U5","IC",["1","2","3","4","6","8","10","12","13","14"]),
  ("LED1","LED",None),("LED2","LED",None),("LED3","LED",None),("LED4","LED",None),
  ("R114","R",None),("R115","R",None),("R116","R",None),("R117","R",None),
  ("R78B","R",None),("R84","R",None),("R85","R",None),("R142","R",None),
  ("C20","C",None),("C21","C",None),("C27","C",None),("C40","C",None),
  ("D36","D",None),("D37","D",None),("D38","D",None),("D39","D",None),
  ("D40","D",None),("D41","D",None),
 ],
 "nets":[
  ("P15",["U6.16","U6.5","C20.1","U5.3","R84.1","R114.2","R115.2","R116.2","R117.2"]),
  ("GND",["U6.8","U5.12","C21.1","C27.2","R78B.2"]),
  ("BUSCOM",["R85.1"]),
  ("N_OVERVOLT",["U6.15","C20.2"]),
  ("N_U6_PIN3",["U6.3","R84.2","R85.2","C21.2"]),
  ("N_UV_DET",["U6.1","D39.1","U5.4"]),
  ("N_GF_DET",["U6.13","D40.1","U5.6"]),
  ("N_OT_DET",["U6.10","D41.1","D37.1"]),
  ("N_SURGE_LATCH_OUT",["U6.9","D38.1","U5.10"]),
  ("N_OT_LATCH_OUT",["D37.2","R78B.1","U5.8","D36.2"]),
  ("N_RESET_LATCH",["D39.2","D40.2","D41.2","D38.2","D42.2","D43.2"]),
  ("N_HITEMP",["U6.11","R103.1"]),
  ("N_U6_7",["U6.7","C27.1"]),
  ("N_U6_COMMON_IN",["U6.14","U6.4","U6.12","U6.6","U7C.6"]),
  ("N_LED_UV",["U5.2","LED1.2"]),("N_LED_UV_A",["LED1.1","R114.1"]),
  ("N_LED_GF",["U5.1","LED2.2"]),("N_LED_GF_A",["LED2.1","R115.1"]),
  ("N_LED_OT",["U5.14","LED3.2"]),("N_LED_OT_A",["LED3.1","R116.1"]),
  ("N_LED_SURGE",["U5.13","LED4.2"]),("N_LED_SURGE_A",["LED4.1","R117.1"]),
  ("N_J5_MOTOR_B",["R142.1"]),
  ("N_T1_3",["R142.2","C40.1","T1.3"]),
  ("N_MOTOR_B",["C40.2","Q6.D"]),
 ],
}

SECTIONS["S7_moddemod"] = {
 "parts":[
  ("TP7","TP",["1"]),("R103","R",None),("D25","D",None),("R91","R",None),
  ("U9B","OPAMP",["5","6","7"]),("TEMPSENSOR","BLOCK",["OUT"]),
  ("R102","R",None),("C23","C",None),("R90","R",None),("D19","D",None),
  ("R88","R",None),("R89","R",None),("C22","C",None),("S1","JUMPER",["1","2"]),
  ("U7B","IC",["3","4"]),("U7C","IC",["5","6"]),("D42","D",None),("D43","D",None),
  ("R131","R",None),("C38","C",None),("R132","R",None),("Q5","PNP",["B","C","E"]),
  ("C39","C",None),("R130","R",None),("C43","C",None),
  ("Q7","NMOS",["S","D","E"]),("Q6","NMOS",["S","D","E"]),
  ("R134","R",None),("C36","C",None),("C41","C",None),("R133","R",None),("C37","C",None),
  ("T1","XFMR",["1","2","3","4"]),("T2","XFMR",["1","2","3","4","5","6"]),
 ],
 "nets":[
  ("GND",["U9B.5","C23.2","C22.2","S1.2","R130.2","C43.2","Q7.S","R134.2","C37.2","T2.4"]),
  ("P15",["D19.2","R88.1","R132.1","R131.1","C38.1","T2.1"]),
  ("N_HITEMP",["R103.1","R102.1","C23.1"]),
  ("N_R103_D25",["R103.2","D25.1"]),
  ("N_D25K",["D25.2","R91.1"]),
  ("N_U9B_INV",["R91.2","U9B.6","R13.2"]),
  # AUDIT: TP7 is NOT on the ECC output - the TP7 vertical (x=1803) crosses the ECC
  # run (y=1722) with no dot. ECC instead runs right/up and reaches the D36 anode.
  ("N_ECC",["U9B.7","D36.1"]),
  ("N_TEMPSENS_OUT",["TEMPSENSOR.OUT","R102.2"]),
  ("N_TEMPTRIP",["R90.2","D19.1","R88.2","R89.1","C22.1","U7B.3"]),
  ("N_S1_R89",["R89.2","S1.1"]),
  ("N_U7B4_U7C5",["U7B.4","U7C.5","D42.1"]),
  ("N_RESET_LATCH",["D42.2","D43.2"]),
  ("N_U7C_OUT",["U7C.6"]),
  ("N_TP7",["TP7.1","R95.1"]),
  ("N_MODIN",["C43.1","T1.1"]),   # AUDIT: y~1754 run goes left to x~2894 then down; not the TP7 node
  ("N_Q5_E",["Q5.E","R131.2","C38.2"]),
  ("N_Q5_B",["Q5.B","R132.2","R130.1","C39.1"]),
  ("N_T2_2",["C39.2","T2.2"]),
  ("N_Q5_C",["Q5.C","C36.2","C37.1","T2.3"]),
  ("N_Q7_GATE",["Q7.E","R134.1","C36.1"]),
  ("N_T1_2",["T1.2","Q7.D"]),
  ("N_T1_3",["T1.3","R142.2","C40.1"]),
  ("N_MOTOR_B",["Q6.D","C40.2"]),
  ("N_T1_4",["T1.4","Q6.S","T2.6","R133.2"]),
  ("N_Q6_GATE",["Q6.E","C41.2","R133.1"]),
  ("N_T2_5",["T2.5","C41.1"]),
 ],
}

SECTIONS["S8_pwmdrv"] = {
 "parts":[
  ("R94","R",None),("R95","R",None),("U9A","OPAMP",["1","2","3","4","8"]),("R104","R",None),
  ("PWM","BLOCK",["1","2","3","4"]),("CLOCK","BLOCK",["1"]),
  ("R73","R",None),("R76","R",None),("LOCKOUT","BLOCK",["1","2","3","4","5","6"]),
  ("DRIVER1","BLOCK",["1","2","3","4"]),("DRIVER2","BLOCK",["1","2","3","4"]),
  ("T4","XFMR",["1","2","3","4","5","6","7","8","9"]),
  ("T3","XFMR",["1","2","3","4","5","6","7","8","9"]),
  ("R137","R",None),("C56","CPOL",None),("C61","CPOL",None),
 ],
 "nets":[
  ("N_R94_UP",["R94.1"]),   # AUDIT: x=1863 vertical, a separate net from both ECC and TP7
  ("N_TP7",["R95.1","TP7.1"]),
  ("N_U9_SUM",["R94.2","R95.2","U9A.2"]),
  ("N_U9_NONINV",["U9A.3","R104.1"]),
  ("GND",["R104.2","C56.2","C61.2"]),
  ("P15",["U9A.8","R137.1","C56.1"]),
  ("N15",["U9A.4"]),
  ("N_U9_OUT",["U9A.1","PWM.1"]),
  ("N_CLK_OUT",["CLOCK.1","PWM.2"]),
  ("N_PWM_OUTA",["PWM.3","R73.1"]),
  ("N_R73_LO",["R73.2","LOCKOUT.1"]),
  ("N_PWM_OUTB",["PWM.4","R76.1"]),
  ("N_R76_LO",["R76.2","LOCKOUT.2"]),
  ("N_LO_OUTA",["LOCKOUT.3","DRIVER1.1"]),
  ("N_LO_OUTB",["LOCKOUT.4","DRIVER2.1"]),
  ("N_LOCKOUT_INH1",["LOCKOUT.5","J1.13"]),
  ("N_LOCKOUT_INH2",["LOCKOUT.6","U4B.1"]),
  ("N_T4P3",["DRIVER1.2","T4.3"]),
  ("N_XFMR_CT",["DRIVER1.3","T4.2","DRIVER2.3","T3.2","R137.2","C61.1"]),
  ("N_T4P1",["DRIVER1.4","T4.1"]),
  ("N_T3P3",["DRIVER2.2","T3.3"]),
  ("N_T3P1",["DRIVER2.4","T3.1"]),
 ],
}

SECTIONS["S9_output"] = {
 "parts":[
  ("J5","CONN",["1","2","4","5","7","8","10","11"]),("C51","CPOL",None),
  ("R157","R",None),("R156","R",None),("R144","R",None),("R151","POT",None),
  ("SURGE_DETECTOR","BLOCK",["IN","OUT"]),
  ("Q14","NPN",["B","C","E"]),("Q12","NPN",["B","C","E"]),
  ("Q9","NPN",["B","C","E"]),("Q11","NPN",["B","C","E"]),
  ("C55","C",None),("R149","R",None),("C53","C",None),("R155","R",None),
  ("R135","R",None),("C44","C",None),("R153","R",None),("C52","C",None),
  ("D78A","D",None),("D78B","D",None),("D78C","D",None),("D78D","D",None),
  ("D47","D",None),("D46","D",None),("D53","D",None),("D52","D",None),
  ("D51","D",None),("D50","D",None),("D48","D",None),("D49","D",None),
  ("R136","R",None),("R154","R",None),("R150","R",None),("R147","R",None),
  ("RGF","R",None),("FGF","BLOCK",["1","2"]),
 ],
 "nets":[
  ("N_DCBUS",["J5.1","J5.2","C51.1","R156.1","R151.1"]),
  ("BUSCOM",["J5.4","J5.5","C51.2","D78C.1","D78D.1","Q11.E","R153.2","C52.2","R154.2",
             "Q12.E","R155.2","C53.2","R147.2","FGF.1"]),
  ("N_DCBUS_SW",["R156.2","R144.2","D78A.2","D78B.2","Q9.C","Q14.C"]),
  ("N_MOTOR_A",["J5.7","J5.8","D78A.1","D78C.2","Q14.E","Q12.C","R150.2","R149.2","C55.2"]),
  ("N_MOTOR_B",["R157.2","D78B.1","D78D.2","Q9.E","Q11.C","R136.2","R135.2","C44.2"]),
  ("N_J5_MOTOR_B",["J5.10","J5.11","R157.1","R142.1"]),
  ("N_R151TAP",["R151.2","SURGE_DETECTOR.IN"]),
  ("N_R144_R151",["R144.1","R151.3"]),
  ("N_SURGE_OUT",["SURGE_DETECTOR.OUT","U7D.11"]),
  ("N_Q9_B",["Q9.B","R135.1","C44.1","D47.2","D46.2"]),
  ("N_T3_7",["T3.7","D47.1"]),("N_T3_9",["T3.9","D46.1"]),("N_T3_8",["T3.8","R136.1"]),
  ("N_Q11_B",["Q11.B","R153.1","C52.1","D53.2","D52.2"]),
  ("N_T4_4",["T4.4","D53.1"]),("N_T4_6",["T4.6","D52.1"]),("N_T4_5",["T4.5","R154.1"]),
  ("N_Q14_B",["Q14.B","R149.1","C55.1","D51.2","D50.2"]),
  ("N_T4_7",["T4.7","D51.1"]),("N_T4_9",["T4.9","D50.1"]),("N_T4_8",["T4.8","R150.1"]),
  ("N_Q12_B",["Q12.B","R155.1","C53.1","D48.2","D49.2"]),
  ("N_T3_4",["T3.4","D48.1"]),("N_T3_6",["T3.6","D49.1"]),("N_T3_5",["T3.5","R147.1"]),
  ("N_GF_MID",["FGF.2","RGF.2"]),
  ("CHASSIS",["RGF.1","R36.2"]),
 ],
}


# ---------------------------------------------------------------- roles ----
# Which pin is the base, which is the output. Read off the drawing and the net
# names, because the alternative -- inferring a pin's role from its position in
# the declaration above -- is wrong for every part whose pins are numbered
# rather than named. It had U1A's output on the left, U4A's collector in the
# base slot, and Q7's grounded source where its gate should be.
#
# Vocabulary: amplifiers use out / in- / in+ / v+ / v-, bipolars b / c / e,
# field-effect g / d / s. Pins not named here are still drawn; they just carry
# no special position.
#
# Parts whose pins are already named B/C/E or D/G/S need no entry -- the name
# is the role. That leaves the sixteen below.
ROLES = {
    # U1 is an 8-pin dual: 1/2/3 = out/in-/in+, 5/6/7 = in+/in-/out, 4/8 = rails.
    "U1A": {"out": "1", "in-": "2", "in+": "3"},
    "U1B": {"v-": "4", "in+": "5", "in-": "6", "out": "7", "v+": "8"},
    "U9B": {"in+": "5", "in-": "6", "out": "7"},
    "U9A": {"out": "1", "in-": "2", "in+": "3", "v-": "4", "v+": "8"},
    "U8A": {"out": "1", "in-": "2", "in+": "3"},
    "U8B": {"v-": "4", "in+": "5", "in-": "6", "out": "7", "v+": "8"},

    # U2 is a quad: sections at 1/2/3, 5/6/7, 8/9/10, 12/13/14.
    "U2A": {"out": "1", "in-": "2", "in+": "3"},   # 1 and 2 tied: unity follower
    "U2C": {"out": "8", "in-": "9", "in+": "10"},
    "U2B": {"in+": "12", "in-": "13", "out": "14"},

    # U3 comparator: pin 13 is the output -- S2_avamp names that node N_U3_OUT.
    "U3":  {"in+": "10", "in-": "11", "out": "13"},

    # U4 is a transistor array. The base is the middle pin of each section;
    # A and B run collector-base-emitter, C and D run emitter-base-collector.
    "U4A": {"c": "12", "b": "13", "e": "14"},
    "U4B": {"c": "1",  "b": "2",  "e": "3"},
    "U4C": {"e": "8",  "b": "9",  "c": "10"},
    "U4D": {"e": "5",  "b": "6",  "c": "7"},

    # Q6/Q7 are transcribed S/D/E, but the gate is the pin the drawing calls
    # "E" -- S7_moddemod names those nodes N_Q6_GATE and N_Q7_GATE.
    "Q7":  {"s": "S", "d": "D", "g": "E"},
    "Q6":  {"s": "S", "d": "D", "g": "E"},
}

# A pin already named for its role needs no table entry.
ROLE_FROM_PIN_NAME = {
    "B": "b", "C": "c", "E": "e",
    "G": "g", "D": "d", "S": "s",
}


# ------------------------------------------------------------ scan layout ----
# Where each part sits on the original drawing, so the generated sheets can be
# arranged like it rather than on a grid. Optional and incremental: a part with
# no entry is auto-placed as before, so this can be filled in one block at a
# time and every partial state still builds.
#
# Coordinates are pixels in the 400 dpi scan of page 30, landscape, origin top
# left, y increasing downward. They are mapped per sheet: the bounding box of
# one block's known positions is fitted to that block's page, preserving aspect
# ratio, so a block keeps its shape without inheriting the empty space around
# it on the D-size original.
SCAN = {
    "dpi": 400,
    "size_px": (6720, 4336),      # landscape, after the page's /Rotate 270
    "y_down": True,
    # One fixed scale for scan placement, rather than fitting each block to its
    # page. Symbol sizes are chosen in millimetres, so the mapping from scan
    # pixels has to be known in advance or the two disagree -- which is what
    # left the function blocks three times too small for the wires drawn round
    # them. At 0.2 a resistor on the drawing comes out near our 15 mm symbol.
    "mm_per_px": 0.2,
}

# Which side of a function block each pin comes out of. Same lesson as ROLES:
# putting every numbered pin on the left because it is numbered is a positional
# guess, and it puts PWM's two outputs on its input side, so the traced wires
# have to detour round the box to reach them. The nets say which is which --
# PWM.1 comes from U9A, PWM.3 goes to R73.
BLOCK_SIDES = {
    "PWM":     {"left": ["1", "2"], "right": ["3", "4"]},
    "LOCKOUT": {"left": ["1", "2", "5", "6"], "right": ["3", "4"]},
    "CLOCK":   {"left": [], "right": ["1"]},
    "DRIVER1": {"left": ["1"], "right": ["2", "3", "4"]},
    "DRIVER2": {"left": ["1"], "right": ["2", "3", "4"]},
}

# How big a part is drawn on the sheet, in scan pixels. Only the kinds whose
# symbol has no natural size need it: the named function blocks, the drivers
# and the transformers. A resistor is a resistor at any scale.
#
# Without this the traced wires -- drawn to meet the original's boxes -- run
# past our smaller ones and reach them by a long detour, which is what made
# sheet 8 look like wires with boxes parked beside them.
EXTENTS = {
    "PWM":     (249, 223),
    "LOCKOUT": (288, 234),
    "CLOCK":   (163, 134),
    "DRIVER1": (69, 183),
    "DRIVER2": (69, 183),
    "T3":      (100, 183),
    "T4":      (100, 183),
}

# refdes -> (x_px, y_px) or (x_px, y_px, rotation).
#
# S8_pwmdrv is transcribed properly, read at 8x zoom off the modulator chain
# along the bottom of the sheet. Rotation is EAGLE's: R270 turns a part so its
# pin 1 points up, which is how the drawing stands R104 and the two electrolytics
# on end above their ground symbols.
POSITIONS = {
    "R94":     (2127, 2490),
    "R95":     (2127, 2558),
    "U9A":     (2241, 2587),
    "R104":    (2165, 2661, "R270"),
    "PWM":     (2517, 2664),
    "CLOCK":   (2273, 2859),
    "R73":     (2706, 2590),
    "R76":     (2706, 2736),
    "LOCKOUT": (2937, 2664),
    "DRIVER1": (3481, 2553),
    "DRIVER2": (3481, 2770),
    "T4":      (3641, 2553),
    "T3":      (3641, 2770),
    "R137":    (3470, 3162),
    "C56":     (3398, 3238, "R270"),
    "C61":     (3561, 3238, "R270"),
}

# net -> [(from_pin, to_pin, [(x_px, y_px), ...]), ...]
#
# One entry per drawn run, in the same scan pixel space. The endpoints name the
# pins they land on, which is what turns this into a second, independent record
# of connectivity: the pins these runs reach must equal the pins the netlist
# says the net has, and where they disagree one of the two readings is wrong.
# A run that only joins other runs -- the centre-tap spine below -- has None at
# that end.
#
# The generated symbols are not the 1985 symbols, so a run's endpoint lands near
# its pin rather than on it. ScanRouter reconciles the last stretch onto the
# real pin; see route.py.
WIRES = {
    "N_U9_OUT": [
        ("U9A.1", "PWM.1", [(2304, 2587), (2392, 2587)]),
    ],
    "N_CLK_OUT": [
        ("CLOCK.1", "PWM.2", [(2273, 2793), (2273, 2739), (2392, 2739)]),
    ],
    "N_PWM_OUTA": [
        ("PWM.3", "R73.1", [(2641, 2590), (2676, 2590)]),
    ],
    "N_R73_LO": [
        ("R73.2", "LOCKOUT.1", [(2738, 2590), (2793, 2590)]),
    ],
    "N_PWM_OUTB": [
        ("PWM.4", "R76.1", [(2641, 2736), (2676, 2736)]),
    ],
    "N_R76_LO": [
        ("R76.2", "LOCKOUT.2", [(2738, 2736), (2793, 2736)]),
    ],
    "N_LO_OUTA": [
        ("LOCKOUT.3", "DRIVER1.1", [(3081, 2590), (3447, 2590)]),
    ],
    "N_LO_OUTB": [
        ("LOCKOUT.4", "DRIVER2.1", [(3081, 2739), (3447, 2739)]),
    ],
    "N_T4P3": [
        ("DRIVER1.2", "T4.3", [(3515, 2479), (3595, 2479)]),
    ],
    "N_T4P1": [
        ("DRIVER1.4", "T4.1", [(3515, 2627), (3595, 2627)]),
    ],
    "N_T3P3": [
        ("DRIVER2.2", "T3.3", [(3515, 2684), (3595, 2684)]),
    ],
    "N_T3P1": [
        ("DRIVER2.4", "T3.1", [(3515, 2841), (3595, 2841)]),
    ],
    "N_U9_SUM": [
        ("R94.2", "U9A.2", [(2167, 2490), (2176, 2490), (2176, 2545), (2190, 2545)]),
        ("R95.2", None, [(2167, 2558), (2176, 2558), (2176, 2545)]),
    ],
    "N_U9_NONINV": [
        ("U9A.3", "R104.1", [(2188, 2636), (2165, 2636), (2165, 2644)]),
    ],
    "N_XFMR_CT": [
        (None, "C61.1", [(3561, 2550), (3561, 3238)]),
        ("DRIVER1.3", "T4.2", [(3515, 2550), (3584, 2550)]),
        ("DRIVER2.3", "T3.2", [(3515, 2770), (3584, 2770)]),
        ("R137.2", None, [(3510, 3162), (3561, 3162)]),
    ],
}


# ------------------------------------------------------------- windings ----
# Which pins belong to which coil, so a transformer can be drawn as coupled
# windings rather than as an anonymous box. Order within a group is the order
# down the coil, so a centre tap sits in the middle.
#
# T3 and T4 are certain: pins 1/2/3 are the primary with pin 2 the centre tap
# -- it lands on N_XFMR_CT alongside both DRIVER centre taps and R137 -- and
# 4/5/6 and 7/8/9 are the two secondaries, each with its middle pin feeding a
# base resistor and its outer pins feeding a diode pair.
#
# T1 and T2 are inferred from the same numbering convention rather than from a
# giveaway net, so they are the ones to check against the scan.
WINDINGS = {
    "T1": [["1", "2"], ["3", "4"]],
    "T2": [["1", "2", "3"], ["4", "5", "6"]],
    "T3": [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]],
    "T4": [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]],
}
