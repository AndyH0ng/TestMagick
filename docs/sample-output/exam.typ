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
  #text(size: 10.5pt)[#"2026-02-23"]
  
]

#v(10pt)
#line(length: 100%, stroke: 0.8pt)
#v(8pt)

// ─── Student Info ───
#grid(
  columns: (1fr, 1fr),
  column-gutter: 20pt,
  row-gutter: 10pt,
  [Name: #box(width: 1fr, stroke: (bottom: 0.4pt + luma(160)), outset: (bottom: 2pt))[#h(1fr)]],
  [Student ID: #box(width: 1fr, stroke: (bottom: 0.4pt + luma(160)), outset: (bottom: 2pt))[#h(1fr)]],
)

#v(12pt)

// ─── Instructions ───
#block(
  width: 100%,
  inset: (x: 10pt, y: 8pt),
  stroke: 0.4pt + luma(180),
)[
  #set text(size: 9.5pt)
  #text(weight: "bold")[Instructions:]
  This exam contains 4 question(s) for a total of 9.0 points.
  Show all work where applicable. Point values are indicated for each problem.
]

#v(16pt)

// ─── Problems ───

#block(
  width: 100%,
  breakable: true,
  above: 0pt,
  below: 0pt,
)[
  #text(weight: "bold", size: 11pt)[1.] #h(2pt)
  #text(size: 9.5pt)[\(2.0 pts\)]
  #v(3pt)

Solve $x^2 - 5x + 6 = 0$. Which option contains all real roots?



  #v(7pt)
  #pad(left: 16pt)[

    #block(spacing: 7pt)[(A) #h(4pt) $x=1,2$]

    #v(4pt)


    #block(spacing: 7pt)[(B) #h(4pt) $x=2,3$]

    #v(4pt)


    #block(spacing: 7pt)[(C) #h(4pt) $x=-2,-3$]

    #v(4pt)


    #block(spacing: 7pt)[(D) #h(4pt) $x=3,6$]


  ]

]

#block(
  width: 100%,
  breakable: true,
  above: 18pt,
  below: 0pt,
)[
  #text(weight: "bold", size: 11pt)[2.] #h(2pt)
  #text(size: 9.5pt)[\(3.0 pts\)]
  #v(3pt)

Read the following code and state what it prints.
#raw(block: true, lang: "python", "total = 0\nfor i in range(1, 5):\n    total += i\nprint(total)")



  #v(8pt)
  #pad(left: 16pt)[
    #block(
      width: 100%,
      height: 30pt,
      stroke: (bottom: 0.4pt + luma(200)),
    )[]
  ]

]

#block(
  width: 100%,
  breakable: true,
  above: 18pt,
  below: 0pt,
)[
  #text(weight: "bold", size: 11pt)[3.] #h(2pt)
  #text(size: 9.5pt)[\(2.0 pts\)]
  #v(3pt)

#"Which OOP principle hides internal implementation details behind a public interface?"



  #v(7pt)
  #pad(left: 16pt)[

    #block(spacing: 7pt)[(A) #h(4pt) #"Inheritance"]

    #v(4pt)


    #block(spacing: 7pt)[(B) #h(4pt) #"Polymorphism"]

    #v(4pt)


    #block(spacing: 7pt)[(C) #h(4pt) #"Encapsulation"]

    #v(4pt)


    #block(spacing: 7pt)[(D) #h(4pt) #"Abstraction leakage"]


  ]

]

#block(
  width: 100%,
  breakable: true,
  above: 18pt,
  below: 0pt,
)[
  #text(weight: "bold", size: 11pt)[4.] #h(2pt)
  #text(size: 9.5pt)[\(2.0 pts\)]
  #v(3pt)

#"State one benefit of creating a weekly study schedule."



  #v(8pt)
  #pad(left: 16pt)[
    #block(
      width: 100%,
      height: 30pt,
      stroke: (bottom: 0.4pt + luma(200)),
    )[]
  ]

]
