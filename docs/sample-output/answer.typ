// ─── Page Setup ───
#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 22mm, left: 25mm, right: 25mm),
  footer: context {
    set text(size: 8.5pt, fill: luma(140))
    align(center)[Page #counter(page).display() of #counter(page).final().first()]
  },
)

#set text(
  font: ("New Computer Modern", "NanumMyeongjo", "AppleMyungjo", "Libertinus Serif"),
  size: 11pt,
  lang: "ko",
)

#set par(
  leading: 0.72em,
  first-line-indent: 0pt,
  justify: true,
)

// ─── Header ───
#align(center)[
  
  #text(size: 12pt, weight: "bold")[#"Study Skills 101"]
  #v(2pt)
  
  #text(size: 16pt, weight: "bold")[#"Sample Set"]
  #v(2pt)
  #text(size: 12pt, weight: "bold")[Answer Key]
  
  #v(2pt)
  #text(size: 10.5pt)[#"2026-02-23"]
  
]

#v(10pt)
#line(length: 100%, stroke: 0.8pt)

// ─── Answer Summary Table ───
#v(14pt)
#align(center)[
  #text(size: 10.5pt, weight: "bold")[Answer Summary]
]
#v(6pt)
#align(center)[
  #table(
    columns: (38pt, 38pt, 38pt, 38pt),
    align: center + horizon,
    stroke: 0.4pt + luma(160),
    inset: 6pt,
    ..for i in range(4) {
      (table.cell(fill: luma(240))[#text(size: 8.5pt, weight: "bold")[#str(i + 1)]],)
    },

    [#text(size: 9.5pt, weight: "bold")[B]],

    [#text(size: 9.5pt, weight: "bold")[TEXT]],

    [#text(size: 9.5pt, weight: "bold")[C]],

    [#text(size: 9.5pt, weight: "bold")[TEXT]],

  )
]

#v(20pt)
#line(length: 100%, stroke: 0.4pt + luma(180))
#v(16pt)

// ─── Detailed Solutions ───

#block(
  width: 100%,
  breakable: true,
  above: 0pt,
  below: 0pt,
)[
  #grid(
    columns: (auto, 1fr, auto),
    align: horizon,
    text(weight: "bold", size: 11pt)[1. \[Q1\]],
    [],
    text(size: 9.5pt, weight: "bold")[Answer: B.],
  )

  #v(4pt)
  #pad(left: 16pt)[

$x=2,3$

  ]


  #v(3pt)
  #pad(left: 16pt)[
    #set text(size: 9pt, fill: luma(120), style: "italic")

    Source: #"sample"

  ]



  #v(8pt)
  #line(length: 100%, stroke: 0.3pt + luma(210))

]

#block(
  width: 100%,
  breakable: true,
  above: 14pt,
  below: 0pt,
)[
  #grid(
    columns: (auto, 1fr, auto),
    align: horizon,
    text(weight: "bold", size: 11pt)[2. \[Q2\]],
    [],
    text(size: 9.5pt, weight: "bold")[Answer: TEXT],
  )

  #v(4pt)
  #pad(left: 16pt)[

#"10"

  ]


  #v(3pt)
  #pad(left: 16pt)[
    #set text(size: 9pt, fill: luma(120), style: "italic")

    Source: #"sample"

  ]



  #v(8pt)
  #line(length: 100%, stroke: 0.3pt + luma(210))

]

#block(
  width: 100%,
  breakable: true,
  above: 14pt,
  below: 0pt,
)[
  #grid(
    columns: (auto, 1fr, auto),
    align: horizon,
    text(weight: "bold", size: 11pt)[3. \[Q3\]],
    [],
    text(size: 9.5pt, weight: "bold")[Answer: C.],
  )

  #v(4pt)
  #pad(left: 16pt)[

#"Encapsulation"

  ]


  #v(3pt)
  #pad(left: 16pt)[
    #set text(size: 9pt, fill: luma(120), style: "italic")

    Source: #"sample"

  ]



  #v(8pt)
  #line(length: 100%, stroke: 0.3pt + luma(210))

]

#block(
  width: 100%,
  breakable: true,
  above: 14pt,
  below: 0pt,
)[
  #grid(
    columns: (auto, 1fr, auto),
    align: horizon,
    text(weight: "bold", size: 11pt)[4. \[Q4\]],
    [],
    text(size: 9.5pt, weight: "bold")[Answer: TEXT],
  )

  #v(4pt)
  #pad(left: 16pt)[

#"It improves consistency and helps prevent last-minute cramming."

  ]


  #v(3pt)
  #pad(left: 16pt)[
    #set text(size: 9pt, fill: luma(120), style: "italic")

    Source: #"sample"

  ]



]
