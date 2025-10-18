# GenReport — SPECIFICATION

Detta dokument beskriver hur GenReport genererar släktrapporter (”Persongalleri”) i Markdown-format.

Syftet är att fungera som **referens för utveckling och testning** — det vill säga, koden ska kunna valideras mot denna beskrivning.

---

## Individsnumrering (”#ID”)

**Mål:** Stabil, deterministisk numrering per körning, baserat på valt rot-ID. Ingen persistens mellan körningar.

1. **Rotperson**  
   - Den valda roten (t.ex. `@I1@` eller `1`) får alltid **`#0`**.

2. **Förfäder (ancestors)**  
   - Numreras **sekventiellt uppåt** från `#1` och framåt i **generationsordning** ut från roten:  
     - Generation 1: föräldrar till roten → lägre nummer än generation 2.  
     - Generation 2: far-/morföräldrar, osv.  
   - **Inom samma generation:** sortera **äldst → yngst** (vid lika födelseår: alfabetiskt på namn).

3. **Icke-förfäder (övriga släktgrenar & personer)**  
   - Startar vid nästa **hela tusental** efter sista förfäder-ID:t.  
     - Ex: finns ~1500 förfäder → starta icke-förfäder vid **`#2000`**.  
     - Om förfäder slutar vid `#999`, starta vid `#1000`; om vid `#1573`, start vid `#2000`.
   - **Ordning för icke-förfäder:**  
     - Gå i **generationer från roten**: gen 0 (roten & dess syskon/makar/barn utanför förfäder), sedan gen 1, gen 2, …  
     - **Syskon:** **äldst → yngst** (vid lika: alfabetiskt).  
     - **”Vänster→höger”** inom samma nivå = deterministisk ordning: (1) födelseår, (2) namn).

4. **Konnektivitet (strict)**  
   - Alla individer i GED ska vara **kopplade** till roten via familj-/relationslänkar.  
   - Om ”öar” hittas (helt okopplade personer) → **stopp** med tydlig lista över namn & årtal, samt info att körningen kan tillåtas med ”allow-islands” (om vi inför sådan flagg) – men **standard** är strikt.

### Specialfall – ”Seven siblings”  
En grupp på sju syskon som inte är kopplade till huvudträdet men som ska behållas i utdata.  
De får egna fasta ID:n i serien **#9001–#9007**, skrivs alltid ut, och genererar ingen varning om frånkoppling.  
Deras GED-ID:n är:
```
@I501665@, @I501670@, @I501674@, @I501681@,
@I501682@, @I501683@, @I501684@
```

5. **Särfall / okända kön**  
   - Kön saknas: påverkar bara etiketten ”Far/Mor” (faller tillbaka till **”Förälder:”**).  
   - (Eventuella projekt-specifika undantag kan listas här, men utgångsläge är: inga hårdkodade undantag.)

---

## Fält och etiketter (utdataformat)

### Allmän struktur
Varje individ skrivs ut som:

```
## #<ID> <GIVN> <SURN> <SYMBOLER> <BIRT YEAR>-<DEAT YEAR>
Född: <datum> i <plats> [, Not: <anmärkning>]
Död: <datum> i <plats> [, Not: <anmärkning>]
Far: #<ID> <GIVN> <SURN> <SYMBOLER> <BIRT YEAR>-<DEAT YEAR>
Mor: #<ID> <GIVN> <SURN> <SYMBOLER> <BIRT YEAR>-<DEAT YEAR>
Vigd: #<ID> <GIVN> <SURN> <SYMBOLER> <BIRT YEAR>-<DEAT YEAR>
Barn: #<ID> <GIVN> <SURN> <SYMBOLER> <BIRT YEAR>-<DEAT YEAR>
Syssla: [<datum>, ]<titel> [i <plats>]
Not: <övrig notering>
[övriga fält]
```

Exempel:
```
## #1 Rickard Helge Bergelius ⁞⬤ 1970-
Född: 1970-02-08 i Uppland, Stockholm, S:t Görans sjh [59.334, 18.021]
Far: #2 Rune Ingvar Lindberg ⁞⬤ 1948-
Mor: #3 Annika Margareta Bergelius ⁞ 1949-
Syssla: Teknisk skribent, elektronikingenjör vid KTH
```

### Etiketter och källfältsmappning

| GEDCOM-fält       | Svensk etikett / hantering                           |
|-------------------|-------------------------------------------------------|
| `NAME.GIVN`, `NAME.SURN` | Del av huvudraden (rubrik)                    |
| `BIRT.DATE`, `BIRT.PLAC`, `BIRT.NOTE` | Slås ihop till ”Född:”-raden |
| `DEAT.DATE`, `DEAT.PLAC`, `DEAT.NOTE` | Slås ihop till ”Död:”-raden |
| `PARENT` | ”Far:” eller ”Mor:” beroende på kön |
| `SPOUSE` | ”Vigd:” |
| `CHILD` | ”Barn:” |
| `OCCU`, `OCCU.DATE`, `OCCU.PLAC` | Slås ihop till ”Syssla:” |
| `NOTE`, `INDI.NOTE` | Utskrivs som ”Not:” |
| `EMAIL`, `FILE`, `OBJE` | **Utesluts helt** |
| `DEAT._DESCRIPTION`, `DEAT.AGE` | **Utesluts** |

---

## Sorteringsordning av fält inom individ

1. Född  
2. Död  
3. Far  
4. Mor  
5. Vigd  
6. Barn  (äldst först)
7. Syssla  
8. Not
9. Övriga fält


---

## Sorteringsordning av individer

1. **Root först (#0)**  
2. **Ancestors (1…N)** i generationsordning.  
3. **Non-ancestors (start vid 1000-gräns)** i generationsordning.  
4. **Seven siblings (#9001–#9007)** sist om ej redan i trädet.

---

## Filnamn och format

- Filnamn: `persongalleri.md`  
  - Om filen redan finns: lägg till löpnummer `persongalleri-1.md`, `-2.md`, etc.
- Kodning: **UTF-8**
- Rubrik i filen: `# Persongalleri`
- Format: **Markdown**, optimerat för läsbarhet (ej maskinbearbetning)

---

*Senast uppdaterad: v0.5.0 + dokumentation av “Seven siblings” och fältmappning.*
