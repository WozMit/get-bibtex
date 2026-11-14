# get-bibtex

A command-line utility for finding mathematical references and generating BibTeX entries.

It lets a user perform a basic search in the [zbMATH Open](https://zbmath.org/) database and select a given result. It then attempts to obtain and merge bibliographic information from [MathSciNet's MRef](https://mathscinet.ams.org/mathscinet/freetools/mref) service. The resulting BibTeX entry is printed directly to the terminal.

An internet connection is required to query zbMATH and MathSciNet. No subscription to MathSciNet is required.

## Usage

Start an interactive search:

```bash
get-bibtex
```

The program will ask for a search term:

```text
Search term: regular partitions szemeredi
```

Search directly from the command line:

```bash
get-bibtex "regular partitions szemeredi"
```

The search results are presented in the terminal as:

```text
(1) Regular partitions of graphs                                                        1978
    Endre Szemerédi
    Problèmes combinatoires et théorie des graphes, Orsay 1976, Colloq. int. CNRS No.
    260, 399-401

(2) Szemerédi's partition and quasirandomness                                           1991
    Miklós Simonovits; Vera T. Sós
    Random Struct. Algorithms

(3) The counting lemma for regular \(k\)-uniform hypergraphs                            2006
    Brendan Nagle; Vojtěch Rödl; Mathias Schacht
    Random Struct. Algorithms

(4) Regular partitions of hypergraphs: regularity lemmas                                2007
    Vojtěch Rödl; Mathias Schacht
    Comb. Probab. Comput.
```

and the user is able to select one of these results or refine the search. After a document is selected, the program attempts to locate the corresponding MathSciNet record. If one is found, the available metadata is combined before the final BibTeX entry is printed.

The explicit `-s` / `--search` option can also be used:

```bash
get-bibtex -s "regular partitions szemeredi"
```

Restrict the search to a particular year:

```bash
get-bibtex "regular partitions" -y 1978
```

or to a range of years:

```bash
get-bibtex szemeredi -y 1970-1980
```

Search using a partial or complete citation. Long citation strings are automatically handled using zbMATH's citation-matching service.

```bash
get-bibtex "E. Szemerédi, Regular partitions of graphs, Problèmes combinatoires et théorie des graphes, Colloq. Internat. CNRS, vol. 260, CNRS, Paris, 1978, pp. 399–401"
```

This directly produces:

```text
Found in zbMATH: https://zbmath.org/0413.05055

Searching MathSciNet... https://mathscinet.ams.org/mathscinet/article?mr=540024

@incollection{Szemeredi78,
  title        = {Regular partitions of graphs},
  author       = {Szemer\'{e}di, Endre},
  year         = {1978},
  booktitle    = {Probl\`emes combinatoires et th\'{e}orie des graphes ({C}olloq. {I}nternat. {CNRS}, {U}niv. {O}rsay, {O}rsay, 1976)},
  series       = {Colloq. Internat. CNRS},
  volume       = {260},
  pages        = {399--401},
  publisher    = {CNRS, Paris},
  isbn         = {2-222-02070-0},
  language     = {English},
  keywords     = {05C99},
  mrclass      = {05C35 (10L10)},
  mrnumber     = {540024},
  mrreviewer   = {D.\ A.\ Klarner},
  zbmath       = {3641497},
  zbl          = {0413.05055}
}
```

These commands work with the standalone binaries or with a Python interpreter, e.g., executing them as

```bash
./get-bibtex-linux-x86_64.bin "regular partitions" -y 1978
```

or

```bash
python get-bibtex.py "regular partitions" -y 1978
```

## Running the program

There are two ways to use `get-bibtex`.

### 1. Download and use a prebuilt binary

Each GitHub release provides standalone x86-64 binaries for Windows, Linux, and macOS:

- `get-bibtex-windows-x86_64.exe`
- `get-bibtex-linux-x86_64.bin`
- `get-bibtex-macos-x86_64.bin`

Python is not required when using these binaries.

#### Windows

```powershell
.\get-bibtex-windows-x86_64.exe
```

#### Linux

```bash
chmod +x get-bibtex-linux-x86_64.bin    # make the binary executable (required only once)
./get-bibtex-linux-x86_64.bin
```

#### macOS

```bash
chmod +x get-bibtex-macos-x86_64.bin    # make the binary executable (required only once)
./get-bibtex-macos-x86_64.bin
```

The binaries accept the same command-line arguments as the Python program.

### 2. Run the native Python program

This is the simplest option if Python is already installed. **Python 3.12 or newer is required.**

Run:

```bash
python get-bibtex.py
```

On systems where Python 3 is invoked explicitly:

```bash
python3 get-bibtex.py
```

## Planned features

I would like to expand the functionality of the program to be able to, for example:

- Read a .bib (or .bbl) file directly and add fields or re-create each entry.
- Allow the user to control several (over 20) options that currently have fixed values, such as excluding certain fields in the output, customising the order of the fields, or obtaining raw MathSciNet output.
- Output a citation in TeX format.
- Properly (think through and) implement the current spaghetti modules, fix broken stuff, validate more carefully, etc.

However, I may only do this when I find the time and no other personal project takes priority.