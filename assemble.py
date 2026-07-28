"""Assembles exchange.html from CSS + markup + logic + data."""
import json

CSS = open('_css.txt', encoding='utf-8').read()
REL = json.load(open('related.json'))
CODES = open('codes.txt').read()

# Course titles for the autocomplete. Prefer the full catalogue
# (courses_clean.csv covers ~10,000 courses); fall back to the older
# equivalency-derived titles.json only for anything the catalogue missed.
# This is why a bare code used to appear next to most courses: titles.json
# alone covered barely a fifth of them.
import csv, re as _re
TITLES = {}
try:
    with open('courses_clean.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            code = _re.sub(r'[^A-Z0-9]', '', (r.get('code') or '').upper())
            title = (r.get('title') or '').strip()
            if code and title:
                TITLES[code] = title[:60]
except FileNotFoundError:
    pass
try:
    for code, title in json.load(open('titles.json', encoding='utf-8')).items():
        TITLES.setdefault(code, title)
except FileNotFoundError:
    pass
print(f"titles available: {len(TITLES)}")

BODY = """
<div class="bar">
  <div class="bar-in">
    <div class="mark"><i></i><span class="u">McGill</span><span class="t">Exchange Planner</span></div>
    <div class="un">Unofficial student tool</div>
  </div>
</div>

<div class="hero">
  <div class="hero-in">
    <div class="kicker">Course equivalency search</div>
    <h1>Where can <span>you</span> actually go?</h1>
    <p class="lede">Pick your program, add the courses you've passed and the ones you'll take
      before you leave, and see every partner university ranked by how many courses are
      genuinely open to you — with your faculty's exchange rules already applied.</p>
    <p class="scale">
      <span>Built from <b>11,969</b> past equivalency decisions</span>
      <span><b>481</b> universities</span>
      <span><b>60</b> countries</span>
    </p>
  </div>
</div>

<div class="wrap">

<div class="rail">
  <button class="step on" id="tab1" onclick="goto(1)"><em>1</em>Your program</button>
  <button class="step" id="tab2" onclick="goto(2)"><em>2</em>Your courses</button>
  <button class="step" id="tab3" onclick="goto(3)"><em>3</em>Universities</button>
  <button class="step" id="tab4" onclick="goto(4)"><em>4</em>Course list</button>
</div>

<!-- STEP 1 -->
<div id="s1">
  <div class="card">
    <h2>Your program</h2>
    <div class="fld">
      <label class="lab" for="prog">Degree program</label>
      <select id="prog"><option value="">Select your program</option></select>
    </div>
    <div id="progExtra"></div>
    <div class="g2">
      <div class="fld">
        <label class="lab" for="major">Major or specialization</label>
        <select id="major" disabled><option value="">Choose your degree first</option></select>
        <div class="hint" id="majorHint">This decides what we show you first.</div>
      </div>
      <div class="fld">
        <label class="lab" for="minor">Minor (optional)</label>
        <select id="minor" disabled><option value="">None</option></select>
      </div>
    </div>
    <div class="g3">
      <div class="fld">
        <label class="lab" for="term">When are you going?</label>
        <select id="term"><option value="">Select a term</option></select>
        <div class="termnote" id="termNote"></div>
      </div>
      <div class="fld">
        <label class="lab" for="year">Year level <em>at the time of exchange</em></label>
        <select id="year"><option value="">Select</option>
          <option>U0</option><option>U1</option><option>U2</option><option>U3</option><option>U4</option></select>
      </div>
      <div class="fld">
        <label class="lab" for="cgpa">CGPA</label>
        <input type="number" id="cgpa" placeholder="3.20" min="0" max="4.0" step="0.01" style="width:100%;padding:11px 12px;font-size:15px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--white);color:var(--ink)">
      </div>
    </div>
    <label class="tg"><input type="checkbox" id="finalTerm"> This would be my final (graduating) term</label>
    <div id="gates"></div>
    <div class="actions"><button class="btn" onclick="goto(2)">Continue</button></div>
  </div>
</div>

<!-- STEP 2 -->
<div id="s2" class="hide">
  <div class="card">
    <h2>Your courses</h2>
    <div class="dual">
      <div class="fld" style="margin-bottom:0">
        <label class="lab" for="taken">Courses you've already passed</label>
        <div class="inpwrap">
          <input type="text" id="taken" autocomplete="off" spellcheck="false"
                 placeholder="COMP 250 — type and press Enter">
          <div class="sug" id="sugT"></div>
        </div>
        <div id="errT"></div>
        <div class="chips" id="chips"></div>
      </div>
      <div class="fld" style="margin-bottom:0">
        <label class="lab" for="planned">Courses you'll take <em id="beforeWhen">before you go</em></label>
        <div class="inpwrap">
          <input type="text" id="planned" autocomplete="off" spellcheck="false"
                 placeholder="ECSE 331 — in progress or planned">
          <div class="sug" id="sugP"></div>
        </div>
        <div id="errP"></div>
        <div class="chips" id="chipsP"></div>
      </div>
    </div>
    <div class="hint" style="margin-top:16px">Anything in the right-hand box hasn't happened yet, so
      courses that depend on it are shown as <b>conditional</b> — available only if you actually
      pass it first. Codes are checked against McGill's live catalogue, so typos are caught here
      rather than surfacing as missing results later.</div>
    <div id="predep"></div>
    <div class="actions">
      <button class="btn ghostb" onclick="goto(1)">Back</button>
      <button class="btn" onclick="goto(3)">See universities</button>
    </div>
  </div>
</div>

<!-- STEP 3 -->
<div id="s3" class="hide">
  <div id="blockBox"></div>
  <div id="ruleBox"></div>

  <div class="s3tabs">
    <button class="s3tab on" id="s3a" onclick="s3mode('rank')">Rank universities for me</button>
    <button class="s3tab" id="s3b" onclick="s3mode('course')">Find who offers specific courses</button>
  </div>

  <div id="s3course" class="hide">
    <div class="card">
      <h2>Which universities offer these courses?</h2>
      <div class="fld" style="margin-bottom:0">
        <label class="lab" for="pkg">Add one or more McGill courses</label>
        <div class="inpwrap">
          <input type="text" id="pkg" autocomplete="off" spellcheck="false"
                 placeholder="COMP 251 — build a package, press Enter after each">
          <div class="sug" id="sugPkg"></div>
        </div>
        <div id="errPkg"></div>
        <div class="chips" id="chipsPkg"></div>
        <div class="hint">With one course you'll see every university that offers an equivalent.
          Add more and the list narrows to universities offering <b>all</b> of them — useful for
          checking a whole term's worth of courses is covered in one place.</div>
      </div>
    </div>
    <div class="sum" id="pkgSum"></div>
    <div id="pkgList"></div>
    <div class="actions"><button class="btn ghostb" onclick="goto(2)">Back</button></div>
  </div>

  <div id="s3rank">
  <div class="card">
    <h2>Narrow it down</h2>
    <div class="g2">
      <div class="fld" style="margin-bottom:0">
        <label class="lab" for="fcountry">Country</label>
        <select id="fcountry"><option value="">Anywhere</option></select>
      </div>
      <div class="fld" style="margin-bottom:0">
        <label class="lab" for="fsubj">Subject (optional)</label>
        <select id="fsubj"><option value="">All subjects</option></select>
      </div>
    </div>
    <div class="filters">
      <label class="tg"><input type="checkbox" id="onlyEligible" checked>
        Only count courses I can take</label>
      <label class="tg"><input type="checkbox" id="countCond" checked>
        Include conditional courses in the count</label>
    </div>
  </div>
  <div class="sum" id="uniSum"></div>
  <div id="uniList"></div>
  <div class="actions"><button class="btn ghostb" onclick="goto(2)">Back</button></div>
  </div>
</div>

<!-- STEP 4 -->
<div id="s4" class="hide">
  <div class="card" id="uniHead"></div>
  <div id="cart"></div>
  <div class="filters" style="border:none;padding-top:6px;margin-top:10px">
    <label class="tg"><input type="checkbox" id="showBlocked"> Show blocked and ineligible courses</label>
  </div>
  <div class="sum" id="cSum"></div>
  <div id="cList"></div>
  <div class="actions"><button class="btn ghostb" onclick="goto(3)">All universities</button></div>
</div>

<div class="note">
  <b>Codes ending in XX are level equivalencies, not typos.</b>
  <span class="mono">AFRI 3XX</span> means the host course has no exact McGill match, but McGill
  approved it as generic 300-level African Studies credit. About one in five approved
  equivalencies is one of these. They're useful for elective and complementary slots, but they
  carry no prerequisites and won't satisfy a requirement naming an exact course.
</div>

<div class="note">
  <b>What this tool can and can't tell you.</b>
  Every row is a past McGill decision, not a catalogue of what's offered. A university with no
  entry hasn't been asked — it isn't barred. Prerequisites shown are McGill's; the host sets its
  own entry rules and timetable. Faculty rules are encoded from published policy but simplified,
  and credit values, course categories, and delivery mode aren't in the underlying data. Nothing
  here is an approval: your faculty adviser and the MTCAF or TCAF decide.
</div>

<footer>
  Built from McGill's public Course Equivalency System and Course Catalogue.
  An unofficial student project — not affiliated with or endorsed by McGill University.
</footer>
</div>
"""

JS = r"""
/* ============================================================
   Reference data
   ============================================================ */
const RELATED = __REL__;
const TITLES  = __TITLES__;
const VALID   = new Set(__CODES__.split(' '));

const FAMILY = {
 sci:"BIOL CHEM COMP MATH PHYS PSYC EPSC ATOC ENVR GEOG NSCI ANAT PHGY BIOC MIMM NEUR ESYS QLSC REDM MICR HGEN BINF COGS PHAR LSCI EXMD PATH EPIB",
 eng:"ECSE MECH CIVE CHEE MIME BIEN AERO BMDE FACC MDPH GEPR ARCH URBP",
 arts:"ANTH ARTH CLAS ECON ENGL EAST FREN GERM HIST HISP ISLA ITAL JWST LING LLCU PHIL POLI RELG RUSS SOCI GSFS INDG WMST AFRI CANS CMPL FILM SWRK URBP INTD LACS COMS WCOM SEAD HPSC LIBA GPHL MSUS",
 mgmt:"MGCR ACCT FINE BUSA INSY MRKT ORGB MGPO MGSC RETL CGM",
 faes:"AEBI AECH AEMA AEPH AGEC AGRI ANSC BREE ENTO ENVB FDSC NUTR PLNT SOIL WILD WOOD PARA FAES BTEC LSCI",
 mus:"MUAR MUCO MUHL MUIN MUJZ MUMT MUPD MUPG MUSP MUSR MUTH MUGT MUEN",
 edu:"EDEC EDEE EDER EDES EDKP EDPC EDPE EDPI EDPS EDSL EDEA EDGC EDEM EDTL",
 hlth:"NUR OCC POTH NRSC PUB QCST HSEL"
};
const FAMOF={}; Object.entries(FAMILY).forEach(([f,s])=>s.split(' ').forEach(x=>FAMOF[x]=f));

const SUBJNAME = {
 COMP:"Computer Science",MATH:"Mathematics & Statistics",PHYS:"Physics",CHEM:"Chemistry",
 BIOL:"Biology",PSYC:"Psychology",NSCI:"Neuroscience",ANAT:"Anatomy & Cell Biology",
 PHGY:"Physiology",BIOC:"Biochemistry",MIMM:"Microbiology & Immunology",
 EPSC:"Earth & Planetary Sciences",ATOC:"Atmospheric & Oceanic Sciences",GEOG:"Geography",
 ENVR:"Environment",ECSE:"Electrical & Computer Engineering",MECH:"Mechanical Engineering",
 CIVE:"Civil Engineering",CHEE:"Chemical Engineering",MIME:"Mining & Materials",
 BIEN:"Bioengineering",ARCH:"Architecture",URBP:"Urban Planning",POLI:"Political Science",
 HIST:"History",ENGL:"English",PHIL:"Philosophy",ECON:"Economics",SOCI:"Sociology",
 ANTH:"Anthropology",ARTH:"Art History",LING:"Linguistics",CLAS:"Classics",
 RELG:"Religious Studies",GSFS:"Gender, Sexuality & Feminist Studies",EAST:"East Asian Studies",
 HISP:"Hispanic Studies",ISLA:"Islamic Studies",JWST:"Jewish Studies",INDG:"Indigenous Studies",
 AFRI:"African Studies",FREN:"French",GERM:"German",ITAL:"Italian",RUSS:"Russian",
 LLCU:"Languages & Cultures",FILM:"Cinema Studies",SWRK:"Social Work",
 COMS:"Communication Studies",MGCR:"Management (Core)",MRKT:"Marketing",FINE:"Finance",
 ORGB:"Organizational Behaviour",MGPO:"Strategy & Global Management",
 MGSC:"Operations Management",INSY:"Information Systems",ACCT:"Accounting",
 BUSA:"Business Administration",RETL:"Retail Management",NUTR:"Nutrition",
 FDSC:"Food Science",AGEC:"Agricultural Economics",PLNT:"Plant Science",ANSC:"Animal Science",
 ENTO:"Entomology",BREE:"Bioresource Engineering",WILD:"Wildlife Biology",SOIL:"Soil Science",
 AEBI:"Ag & Env Biology",AEMA:"Ag & Env Mathematics",AEPH:"Ag & Env Physics",
 EDKP:"Kinesiology & Physical Education",EDEC:"Education (Curriculum)",
 EDPE:"Educational Psychology",EDSL:"Second Language Education",MUHL:"Music History",
 MUTH:"Music Theory",MUPD:"Music Performance",LAWG:"Law",PHAR:"Pharmacology",
 WCOM:"Written Communication",INTD:"Interdepartmental",LSCI:"Life Sciences",QLSC:"Quantitative Life Sciences", AECH:"Ag & Env Chemistry", AEHM:"Ag & Env Humanities", AERO:"Aerospace Engineering", AGRI:"Agriculture (General)", BINF:"Bioinformatics", BIOT:"Biotechnology", BMDE:"Biomedical Engineering", BTEC:"Biotechnology", CANS:"Canadian Studies", CATH:"Catholic Studies", CGM:"Career & Management", CMPL:"Comparative Literature", COGS:"Cognitive Science", EDEA:"Education (Arts)", EDEE:"Elementary Education", EDEM:"Educational Leadership", EDER:"Education (Research)", EDGC:"Counselling Psychology", EDPC:"Educational Psychology", EDPI:"Educational Psychology", ENVB:"Environmental Biology", EPIB:"Epidemiology & Biostatistics", ESYS:"Earth System Science", EXMD:"Experimental Medicine", FACC:"Engineering (Faculty Core)", FAES:"Ag & Env Sciences (General)", FRSL:"French as a Second Language", FSCI:"Interdisciplinary Life Sciences", GPHL:"Geophysics", HGEN:"Human Genetics", HPSC:"History & Philosophy of Science", HSEL:"Health Sciences Education", INDR:"Industrial Relations", INLG:"Indigenous Languages", LACS:"Latin American & Caribbean Studies", LIBA:"Liberal Arts (General)", MICR:"Microbiology", MSUS:"Sustainability", MUCO:"Music Composition", MUEN:"Music Ensemble", MUGT:"Music Theory", MUIN:"Music Instrument", MUMT:"Music Technology", MUSR:"Music Research", NEUR:"Neuroscience", NRSC:"Neuroscience", NUR:"Nursing", OCC:"Occupational Therapy", PARA:"Parasitology", PATH:"Pathology", POTH:"Physical & Occupational Therapy", PRV:"Clinical Rotations", PUB:"Public Policy", QCST:"Quebec Studies", SEAD:"Social Entrepreneurship"
};
const subjLabel = s => SUBJNAME[s] ? s+" — "+SUBJNAME[s] : s;

/* ============================================================
   PROGRAMS
   `maj` lists only the specializations that genuinely exist under
   that degree at McGill. Urban Planning, for instance, is a graduate
   program (M.U.P.) and is therefore not offered under B.Sc.(Arch).
   ============================================================ */
const M_ARTS = "AFRI ANTH ARTH CANS CLAS CMPL COMS EAST ECON ENGL FREN GEOG GERM GSFS HISP HIST INDG ISLA ITAL JWST LACS LING LLCU PHIL POLI PSYC RELG RUSS SOCI WCOM".split(' ');
const M_SCI  = "ANAT ATOC BIOC BINF BIOL CHEM COGS COMP EPSC ENVR ESYS GEOG MATH MIMM NSCI PHAR PHGY PHYS PSYC QLSC".split(' ');
const M_MGMT = "ACCT BUSA FINE INSY MGPO MGSC MRKT ORGB RETL".split(' ');
const M_FAES = "AEBI AEMA AEPH AGEC AGRI ANSC ENTO ENVB ENVR FDSC LSCI NUTR PLNT SOIL WILD".split(' ');
const M_EDBED= "EDEC EDEE EDER EDES EDPE EDPI EDSL EDTL".split(' ');
const M_MUS  = "MUCO MUHL MUIN MUJZ MUMT MUPD MUPG MUSR MUTH".split(' ');

const PROGRAMS = [
 {g:"Engineering", items:[
   {id:"eng_ece_ele",n:"B.Eng. Electrical Engineering",f:["eng","ece"],maj:["ECSE"]},
   {id:"eng_ece_cmp",n:"B.Eng. Computer Engineering",f:["eng","ece"],maj:["ECSE"]},
   {id:"eng_ece_sof",n:"B.Eng. Software Engineering",f:["eng","ece"],maj:["ECSE","COMP"]},
   {id:"eng_mech",n:"B.Eng. Mechanical Engineering",f:["eng"],maj:["MECH"]},
   {id:"eng_civ",n:"B.Eng. Civil Engineering",f:["eng"],maj:["CIVE"]},
   {id:"eng_chee",n:"B.Eng. Chemical Engineering",f:["eng"],maj:["CHEE"]},
   {id:"eng_mime",n:"B.Eng. Materials / Mining Engineering",f:["eng"],maj:["MIME"]},
   {id:"eng_bien",n:"B.Eng. Bioengineering",f:["eng"],maj:["BIEN"]},
   {id:"eng_bse",n:"B.S.E. Software Engineering",f:["eng","ece"],maj:["COMP","ECSE"]},
   {id:"eng_arch",n:"B.Sc. (Arch) Architecture",f:["eng","arch"],maj:["ARCH"]},
 ]},
 {g:"Arts", items:[
   {id:"arts_ba",n:"B.A.",f:["arts"],maj:M_ARTS},
   {id:"arts_bsw",n:"B.S.W. Social Work",f:["arts"],maj:["SWRK"]},
   {id:"arts_bth",n:"B.Th. Theology",f:["arts"],maj:["RELG"]},
 ]},
 {g:"Science", items:[
   {id:"sci_bsc",n:"B.Sc.",f:["sci"],maj:M_SCI},
   {id:"sci_basc",n:"B.A. & Sc.",f:["sci","basc"],maj:M_SCI.concat(M_ARTS)},
 ]},
 {g:"Management (Desautels)", items:[
   {id:"mgmt_bcom",n:"B.Com.",f:["mgmt"],maj:M_MGMT},
 ]},
 {g:"Education", items:[
   {id:"edu_bed",n:"B.Ed. (teacher certification)",f:["educ","bed"],maj:M_EDBED},
   {id:"edu_kin",n:"B.Sc. Kinesiology",f:["educ"],maj:["EDKP"]},
   {id:"edu_bae",n:"B.A. Education in Global Contexts",f:["educ"],maj:["EDEC","EDER"]},
 ]},
 {g:"Agricultural & Environmental Sciences", items:[
   {id:"faes_ages",n:"B.Sc. (Ag.Env.Sc.)",f:["faes"],maj:M_FAES},
   {id:"faes_nutr",n:"B.Sc. Nutrition",f:["faes"],maj:["NUTR"]},
   {id:"faes_diet",n:"B.Sc. Dietetics",f:["faes","diet"],maj:["NUTR"]},
   {id:"faes_food",n:"B.Sc. Food Science",f:["faes"],maj:["FDSC"]},
   {id:"faes_bree",n:"B.Eng. Bioresource Engineering",f:["faes","eng","bree"],maj:["BREE"]},
 ]},
 {g:"Music (Schulich)", items:[
   {id:"mus_bmus",n:"B.Mus.",f:["music"],maj:M_MUS},
   {id:"mus_lmus",n:"L.Mus. (Licentiate)",f:["music","nomus"],maj:M_MUS},
 ]},
 {g:"Law", items:[{id:"law_bcljd",n:"BCL/JD",f:["law"],maj:["LAWG"]}]},
 {g:"No exchange pathway", items:[
   {id:"none_med",n:"Medicine",f:["noexch"],maj:[]},
   {id:"none_dent",n:"Dentistry",f:["noexch"],maj:[]},
   {id:"none_nurs",n:"Nursing",f:["noexch"],maj:[]},
 ]},
];

/* Pre-departure course requirements (§3.1.2) */
const PREDEP = {
  eng_ece_ele:{all:["ECSE211","ECSE331","ECSE324"],
               any:{n:2,of:["ECSE307","ECSE308","ECSE362","ECSE354"]},
               note:"Electrical Engineering pre-departure requirement"},
  eng_ece_cmp:{all:["ECSE211","ECSE331","ECSE324","ECSE321","COMP251"],
               note:"Computer Engineering pre-departure requirement"},
  eng_ece_sof:{all:["ECSE211","ECSE324","ECSE321","COMP251"],
               note:"Software Engineering pre-departure requirement"},
  eng_bse:{all:["ECSE211","ECSE324","ECSE321","COMP251"],
           note:"Software Engineering pre-departure requirement"},
};

/* CGPA gates (§4.4) */
const GATE={eng:{cgpa:3.00},arts:{cgpa:3.00},educ:{cgpa:3.00,soft:true},faes:{cgpa:3.00},
  law:{cgpa:2.70},mgmt:{cgpa:3.00},sci:{cgpa:3.00},music:{cgpa:2.70}};

/* BLOCK_TRANSFER lists keyed on McGill course code */
const BLOCK=[
 {scope:"eng",test:c=>/^FACC(300|400)/.test(c),why:"FACC 300/400 must be completed at McGill"},
 {scope:"bed",test:c=>/^EDFE/.test(c),why:"Field experience — CAPFE permits no exemptions, ever"},
 // §3.8.3 full named set
 {scope:"music",test:c=>/^(MUTH15[01]|MUJZ1[67][01])/.test(c),
   why:"Theory / musicianship — placement exam only, never transfer credit"},
 {scope:"music",test:c=>/^MUSP1(23|24|40|41|70|71)/.test(c),
   why:"Musicianship — placement exam only, never transfer credit"},
 // §3.7.14 Chemistry & Physics advanced labs
 {scope:"sci",test:c=>/^(CHEM(367|377)|PHYS(359|446))/.test(c),
   why:"Advanced laboratory — hard-blocked on safety and equipment grounds"},
 // §3.6.6 CPA
 {scope:"cpa",test:c=>/^ACCT/.test(c),why:"CPA track: accounting courses may not be taken outside McGill"},
 {scope:"cpa",test:c=>/^(FINE342|BUSA364)/.test(c),why:"CPA track: explicitly banned from exchange"},
 // §3.4.7 McGill-run field study semesters are not exchanges
 {scope:"faes",test:c=>/^AGRI325/.test(c),
   why:"McGill-run field study course — taught abroad by McGill, not an exchange equivalency"},
];

const WARN=[
 {scope:"sci",test:c=>/^COMP(206|250|251|273|302)/.test(c),
   why:"SOCS core sequence — high rejection rate; syllabus must match McGill exactly"},
 {scope:"sci",test:c=>/^MATH(251|254|255|323|324)/.test(c),
   why:"Math core — rarely approved unless the host is a direct structural match"},
 {scope:"sci",test:c=>/^(PHGY|ANAT|BIOL)[3-9]/.test(c),
   why:"300+ level — requires manual departmental pre-approval before departure"},
 {scope:"sci",test:c=>/^(CHEM|PHYS|BIOL)\d/.test(c)&&/L$/.test(c),
   why:"Lab course — heavily scrutinised, often downgraded to generic credit"},
 {scope:"mgmt",test:c=>/^MGCR/.test(c),why:"Management Core — maximum 9 credits transferable"},
];

/* §3.6.9 destination-level restrictions */
const DESTRULES=[
 {match:u=>/sciences po/i.test(u),
  when:sel=>[...sel.values()].some(r=>r.sub==='MGCR'||r.sub==='FINE'),
  scope:'mgmt',
  why:"Sciences Po will not allow exchange students to take Management Core or Finance courses. Your selection includes MGCR or FINE courses."},
 {match:u=>/HEC Paris/i.test(u),
  when:()=> $('#cegep')&&$('#cegep').checked,
  scope:'mgmt',
  why:"HEC Paris rejects any applicant who completed a French Baccalauréat or attended CEGEP in Quebec, even as a McGill student."},
];
/* Notes attached to specific destinations regardless of the student */
const DESTNOTE=[
 {match:u=>/Peking University|Tsinghua/i.test(u),
  t:"Citizenship restriction",
  b:"This partner does not accept Chinese nationals on exchange through Desautels."},
 {match:u=>/Central Conservatory|Hochschule für Musik|Mozarteum|Norwegian Academy of Music|Queensland Conservatorium|Royal Northern College|Royal Conservat|Sibelius/i.test(u),
  t:"Audition required",
  b:"This is a Schulich conservatory partner. A 10-minute video audition recorded within the previous three months must be emailed to Student Affairs before the application deadline."},
 {match:u=>/Université Catholique de Louvain|Tel Aviv/i.test(u),
  t:"On hold",
  b:"Listed as ON HOLD for 2026–2027 in the Law partner table. Confirm availability with your SAO before planning."},
];

const FACNOTE={
 eng:{t:"CEAB Accreditation Units",k:"warn",b:"Engineering is CEAB-accredited, which constrains Accreditation Units. Taking core or design courses abroad may cause an AU shortfall that delays graduation or affects licensure. Exactly half of a B.Eng./B.S.E. program must be completed at McGill, and that 50% includes CEGEP, AP and IB advanced standing. Online, correspondence and distance courses are not permitted for credit."},
 arch:{t:"B.Sc. (Arch) residency",k:"info",b:"A minimum of 60 credits must be completed at McGill, excluding Year 0 courses."},
 arts:{t:"Arts residency and caps",k:"info",b:"Transfer caps: Minor 6 credits · Major 12 · Joint Honours 12 · Honours 21. At least 60 credits must be completed at McGill, and at least two-thirds of program requirements. A maximum of 12 university-level credits may come from faculties other than Arts and Science across the whole B.A. Faculty approval on the MTCAF covers transfer credit only — never whether a course satisfies a program requirement."},
 sci:{t:"Science: SOUSA is the only authority",k:"info",b:"Only SOUSA can pre-approve courses; departmental approval is a recommendation. At least two-thirds of departmental program requirements must be completed at McGill. Maximum 15 transfer credits per term, 30 for a full year. Online courses are not permitted at all during a McGill Exchange. A study plan of 4–5 courses (12–15 credits) is required — a single-course plan is not a valid application."},
 mgmt:{t:"Desautels caps and the 15-credit rule",k:"info",b:"Transfer caps: Management Core 9 credits · Major 12 · Concentration or Minor 6 · Electives unlimited, with a further 6-credit maximum on generic “Topics in …” courses. You must map exactly 15 McGill credits per term — a full load — regardless of how the host weights its courses. No Pass/Fail or S/U. Experiential Learning must be completed at McGill."},
 educ:{t:"Field experience is immovable",k:"warn",b:"Field experiences and their co-requisite professional seminars must be taken at McGill, for each placement. CAPFE opposes exemptions regardless of prior experience or degrees, and the policy cannot be excepted. An exchange may push your placement to the next time it is offered. A minimum of 60 credits must be completed at McGill; Education publishes no two-thirds program-residency rule."},
 faes:{t:"Two-layer residency — the campus rule usually binds",k:"warn",b:"You must complete 60 credits at McGill (72 for Bioresource Engineering) AND at least two-thirds of your credits at Macdonald Campus. Exchange credits satisfy neither layer. ENVR courses count as Macdonald wherever they are taught. If you entered with CEGEP advanced standing the two-thirds applies to your remaining credits, tightening it further."},
 bree:{t:"Two rule sets apply at once",k:"warn",b:"Bioresource Engineering sits in FAES but is also formally subject to CEAB accreditation. Your courses must satisfy the FAES online and campus limits and the Engineering AU constraints simultaneously."},
 music:{t:"Partially searchable",k:"info",b:"Useful for music history, complementary and elective slots. Applied lessons and large ensembles are matched by audition and studio fit, not by equivalency, and will not reverse-search meaningfully. Schulich administers transfer credit manually — there is no published conversion formula."},
 nomus:{t:"L.Mus. students are not eligible for exchange",k:"stop",b:"Only students enrolled in a Bachelor of Music program are eligible for exchange at Schulich. The Licentiate in Music does not have an exchange pathway."},
 law:{t:"Reverse search does not apply to Law",k:"stop",b:"Exchange credits are strictly elective and can never fulfil a required or complementary course. Every host course is submitted under the single generic code LAWG rather than matched to a McGill course, so there is no course-by-course mapping to search. Maximum 12 outside credits toward the degree, or 15 law credits during an approved exchange term. Selection is by random lottery, not CGPA rank. Contact the Law SAO directly."},
 noexch:{t:"No outgoing exchange pathway",k:"stop",b:"Medicine, Dentistry and Nursing have no outgoing mobility or exchange pathway at McGill. This planner does not apply to your program."},
 basc:{t:"B.A. & Sc. routes through SOUSA",k:"info",b:"B.A. & Sc. students are advised by SOUSA, not Arts OASIS, even for Arts-coded courses."},
 diet:{t:"Dietetics sequence",k:"info",b:"The prescribed Dietetics course sequence inherently satisfies the Macdonald two-thirds requirement, which leaves very little room for exchange credits."},
};

/* Rules that exist in policy but depend on data McGill's equivalency
   database does not publish (delivery mode, campus, live travel
   advisories). We cannot compute these, so we state them plainly rather
   than pretend to enforce them - silence would mislead more than a note. */
const UNENFORCED = [
 {when:p=>p.f.includes('sci'),t:"Online courses are never allowed (Science)",
  b:"SOUSA forbids online, correspondence and distance courses entirely during a McGill Exchange, whatever the subject. The database does not record delivery mode, so confirm each host course is in-person yourself."},
 {when:p=>p.f.includes('mgmt'),t:"Online courses are not accepted (Desautels)",
  b:"Desautels does not accept online courses for transfer. Delivery mode is not in this data — verify each host course is taught in person."},
 {when:p=>p.f.includes('arts'),t:"Online delivery depends on the course's home faculty",
  b:"Arts permits online courses, but a Science-coded (e.g. COMP) or Management-coded (e.g. FINE) course follows that faculty's rule instead, and both forbid online. Check the owning faculty before assuming an online course counts."},
 {when:p=>p.f.includes('mgmt'),t:"Experiential Learning must be done at McGill",
  b:"The B.Com. Experiential Learning requirement cannot be satisfied on exchange. Those specific courses are not individually flagged here."},
 {when:()=>true,t:"Check the Canadian travel advisory yourself",
  b:"Partners in countries under a Level 3 or 4 Government of Canada advisory are not approved for exchange. Advisories change constantly and are not in this data, so verify your destination at travel.gc.ca."},
];

/* ============================================================ */
let DATA=[],READY=false,curUni=null;
const passed=new Set(), planned=new Set();
const $=s=>document.querySelector(s);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const N=s=>String(s).toUpperCase().replace(/[^A-Z0-9]/g,'');
const pretty=c=>c.replace(/^([A-Z]+)(\d.*)$/,'$1 $2');

function prog(){const id=$('#prog').value;
  for(const g of PROGRAMS) for(const it of g.items) if(it.id===id) return it; return null}
function scopes(){const p=prog(); if(!p) return [];
  const s=[...p.f];
  if($('#cpaTrack')&&$('#cpaTrack').checked) s.push('cpa');
  if($('#honours')&&$('#honours').checked) s.push('hon');
  if($('#ibConc')&&$('#ibConc').checked) s.push('ib');
  return s}
/* Faculties with no exchange route at all */
function facultyBlocked(){
  const p=prog(); if(!p) return null;
  if(p.f.includes('noexch')) return FACNOTE.noexch;
  if(p.f.includes('nomus')) return FACNOTE.nomus;
  if(p.f.includes('law')) return FACNOTE.law;
  const ac=$('#admcat');
  if(p.f.includes('law')&&ac&&ac.value!=='regular')
    return {t:'Not eligible: admission category',
            b:'Advanced standing and transfer students are categorically ineligible for exchange at the Faculty of Law.'};
  return null;
}
function major(){return $('#major').value||''}
function minorV(){return $('#minor').value||''}

function relevance(sub){
  const maj=major(),min=minorV();
  if(!maj&&!min) return 2;
  if(sub===maj||(min&&sub===min)) return 3;
  if((RELATED[maj]||[]).includes(sub)) return 2;
  if(maj&&FAMOF[sub]&&FAMOF[sub]===FAMOF[maj]) return 2;
  return 1;
}

/* ---------- terms ---------- */
function buildTerms(){
  const now=new Date(), y=now.getFullYear(), m=now.getMonth();
  const out=[];
  for(let k=0;k<3;k++){
    const yy=y+k;
    out.push({v:'F'+yy,   n:'Fall '+yy,               before:'before September '+yy});
    out.push({v:'W'+(yy+1),n:'Winter '+(yy+1),        before:'before January '+(yy+1)});
    out.push({v:'Y'+yy,   n:'Full year '+yy+'–'+String(yy+1).slice(2), before:'before September '+yy});
  }
  // drop terms already begun
  return out.filter(t=>{
    const yr=parseInt(t.v.slice(1));
    if(t.v[0]==='F'||t.v[0]==='Y') return yr>y||(yr===y&&m<7);
    return yr>y||(yr===y&&m<0);
  }).slice(0,7);
}

/* ---------- data load ---------- */
function boot(){
  const ps=$('#prog');
  PROGRAMS.forEach(gr=>{const og=document.createElement('optgroup');og.label=gr.g;
    gr.items.forEach(it=>{const o=el('option',null,it.n);o.value=it.id;og.appendChild(o)});
    ps.appendChild(og)});

  const ts=$('#term');
  buildTerms().forEach(t=>{const o=el('option',null,t.n);o.value=t.v;o.dataset.before=t.before;ts.appendChild(o)});

  const fc=$('#fcountry');
  [...new Set(DATA.map(d=>d.co).filter(Boolean))].sort()
    .forEach(s=>{const o=el('option',null,s);o.value=s;fc.appendChild(o)});
  const fs=$('#fsubj');
  [...new Set(DATA.map(d=>d.sub))].sort()
    .forEach(s=>{const o=el('option',null,s);o.value=s;fs.appendChild(o)});

  ps.addEventListener('change',()=>{fillMajors();progExtra();gates();predep()});
  ['year','cgpa','finalTerm'].forEach(i=>$('#'+i).addEventListener('change',gates));
  $('#cgpa').addEventListener('input',gates);
  $('#term').addEventListener('change',()=>{termNote();gates();predep()});
  $('#major').addEventListener('change',()=>{renderUnis();if(curUni)renderCart()});
  $('#minor').addEventListener('change',()=>{renderUnis()});
  ['fcountry','fsubj','onlyEligible','countCond'].forEach(i=>
    $('#'+i).addEventListener('change',renderUnis));
  $('#showBlocked').addEventListener('change',renderCourses);

  wireInput('taken','sugT','errT',passed,'chips');
  wireInput('planned','sugP','errP',planned,'chipsP');
  wirePkg();
}

/* ---------- major constrained by degree ---------- */
function subjectsWithVolume(){
  const c={}; DATA.forEach(d=>{if(d.st==='A')c[d.sub]=(c[d.sub]||0)+1});
  return c;
}
function fillMajors(){
  const p=prog(), mj=$('#major'), mn=$('#minor');
  mj.innerHTML=''; mn.innerHTML='';
  if(!p){mj.disabled=mn.disabled=true;
    mj.appendChild(el('option',null,'Choose your degree first'));
    mn.appendChild(el('option',null,'None')); return}
  const cnt=subjectsWithVolume();

  // p.maj is a plain array of subject codes (e.g. M_SCI). Keep only
  // those that actually have equivalency data, and name them nicely.
  let list=(p.maj||[]).filter(s=>cnt[s]).sort((a,b)=>subjLabel(a).localeCompare(subjLabel(b)));

  mj.disabled=list.length===0; mn.disabled=false;
  mj.appendChild(el('option',null,list.length?'Select your field':'Not applicable — no exchange pathway'));
  list.forEach(s=>{const o=el('option',null,subjLabel(s));o.value=s;mj.appendChild(o)});
  if(list.length===1){mj.value=list[0]; window.__MAJOR__=list[0];}

  mn.appendChild(el('option',null,'None'));
  Object.keys(cnt).filter(s=>cnt[s]>=5&&!/XXX$/.test(s))
    .sort((a,b)=>subjLabel(a).localeCompare(subjLabel(b)))
    .forEach(s=>{const o=el('option',null,subjLabel(s));o.value=s;mn.appendChild(o)});

  $('#majorHint').textContent = list.length>1
    ? 'Only fields offered under this degree are listed.'
    : (list.length===1 ? 'This degree has a single field.' : 'This program has no outgoing exchange pathway.');
}

function progExtra(){
  const p=prog(),box=$('#progExtra');box.innerHTML='';
  if(!p)return;
  const add=(html,ids)=>{const w=el('div');w.innerHTML=html;box.appendChild(w);
    ids.forEach(i=>{const e=$('#'+i); if(e) e.addEventListener('change',()=>{gates();renderUnis()})})};

  if(p.f.includes('mgmt')){
    add('<label class="tg" style="margin-bottom:10px"><input type="checkbox" id="cpaTrack"> '+
        'I\'m pursuing the CPA designation</label>'+
        '<label class="tg" style="margin-bottom:10px"><input type="checkbox" id="ibConc"> '+
        'My concentration is International Business</label>'+
        '<label class="tg" style="margin-bottom:14px"><input type="checkbox" id="cegep"> '+
        'I attended CEGEP in Quebec or completed a French Baccalauréat</label>',
        ['cpaTrack','ibConc','cegep']);
  }
  if(p.f.includes('law')){
    add('<div class="fld"><label class="lab" for="admcat">Admission category</label>'+
        '<select id="admcat"><option value="regular">Regular admission</option>'+
        '<option value="adv">Advanced standing</option>'+
        '<option value="transfer">Transfer student</option></select></div>',['admcat']);
  }
  if(p.f.includes('sci')||p.f.includes('arts')){
    add('<label class="tg" style="margin-bottom:14px"><input type="checkbox" id="honours"> '+
        'I\'m in an Honours or Joint Honours program</label>',['honours']);
  }
}

function termNote(){
  const s=$('#term'), o=s.options[s.selectedIndex];
  const b=o&&o.dataset.before?o.dataset.before:'before you go';
  $('#termNote').textContent = o&&o.value ? 'Everything in your "planned" list must be finished '+b+'.' : '';
  $('#beforeWhen').textContent = o&&o.value ? b : 'before you go';
}

/* ---------- course input with validation ---------- */
function wireInput(inputId,sugId,errId,store,chipId){
  const inp=$('#'+inputId), sug=$('#'+sugId), err=$('#'+errId);
  let hl=-1;
  const close=()=>{sug.classList.remove('show');hl=-1};

  inp.addEventListener('input',()=>{
    err.innerHTML='';
    const raw=inp.value.toUpperCase();
    const q=N(inp.value);
    if(q.length<3){close();return}
    // If the user has typed a full 3-4 letter subject prefix followed by a
    // space (e.g. "COMP "), show EVERY course in that subject - no cap.
    // Otherwise fall back to a short prefix autocomplete.
    const subjMatch=raw.match(/^([A-Z]{3,4})\s/);
    let hits;
    if(subjMatch){
      const subj=subjMatch[1];
      const rest=q.slice(subj.length);
      hits=[...VALID].filter(c=>c.startsWith(subj)&&c.slice(subj.length).startsWith(rest)).sort();
    } else {
      hits=[...VALID].filter(c=>c.startsWith(q)).sort().slice(0,10);
    }
    if(!hits.length){close();return}
    sug.innerHTML='';
    hits.forEach(c=>{
      const d=el('div');
      d.appendChild(el('span',null,pretty(c)));
      if(TITLES[c]) d.appendChild(el('span','t',TITLES[c]));
      d.onclick=()=>{add(c)};
      sug.appendChild(d);
    });
    sug.classList.add('show');
  });

  inp.addEventListener('keydown',e=>{
    const items=[...sug.querySelectorAll('div')];
    if(e.key==='ArrowDown'&&items.length){e.preventDefault();hl=Math.min(hl+1,items.length-1)}
    else if(e.key==='ArrowUp'&&items.length){e.preventDefault();hl=Math.max(hl-1,0)}
    else if(e.key==='Escape'){close();return}
    else if(e.key==='Enter'){
      e.preventDefault();
      if(hl>=0&&items[hl]){items[hl].click();return}
      add(N(inp.value)); return;
    } else return;
    items.forEach((x,i)=>x.classList.toggle('hl',i===hl));
    if(items[hl])items[hl].scrollIntoView({block:'nearest'});
  });

  document.addEventListener('click',e=>{if(!e.target.closest('.inpwrap'))close()});

  function add(code){
    err.innerHTML='';
    if(!code){return}
    if(!/^[A-Z]{2,4}\d{3}/.test(code)){
      showErr('“'+inp.value.trim()+'” isn\'t a course code. McGill codes look like COMP 250 — '+
              'two to four letters then three digits.');
      return;
    }
    if(!VALID.has(code)){
      const subj=code.match(/^[A-Z]+/)[0];
      const same=[...VALID].filter(c=>c.startsWith(subj)).sort();
      showErr(same.length
        ? pretty(code)+' doesn\'t exist in McGill\'s catalogue. '+subj+' does — try '+
          same.slice(0,3).map(pretty).join(', ')+'…'
        : 'There\'s no subject code “'+subj+'” at McGill. Check the spelling.');
      return;
    }
    const other = store===passed ? planned : passed;
    if(other.has(code)) other.delete(code);
    store.add(code);
    inp.value=''; close(); drawChips(); predep();
  }
  function showErr(msg){err.innerHTML='';const d=el('div','err',msg);err.appendChild(d);close()}
}

function drawChips(){
  const mk=(set,box,cls)=>{
    const b=$('#'+box); b.innerHTML='';
    [...set].sort().forEach(c=>{
      const ch=el('span','chip'+(cls?' '+cls:''));
      ch.appendChild(el('span',null,pretty(c)));
      const x=el('button',null,'×');
      x.setAttribute('aria-label','Remove '+pretty(c));
      x.onclick=()=>{set.delete(c);drawChips();predep()};
      ch.appendChild(x); b.appendChild(ch);
    });
  };
  mk(passed,'chips',''); mk(planned,'chipsP','plan');
}

/* ---------- pre-departure requirement check ---------- */
/* Returns null when satisfied, otherwise what's still missing.
   Used both in step 2 and as a hard stop in step 3. */
function predepMissing(){
  const p=prog(); if(!p) return null;
  const req=PREDEP[p.id]; if(!req) return null;
  const have=new Set([...passed,...planned]);
  const missAll=(req.all||[]).filter(c=>!have.has(c));
  let missAny=null;
  if(req.any){
    const got=req.any.of.filter(c=>have.has(c)).length;
    if(got<req.any.n) missAny={need:req.any.n-got,of:req.any.of.filter(c=>!have.has(c))};
  }
  if(!missAll.length&&!missAny) return null;
  return {all:missAll,any:missAny,note:req.note};
}

function predep(){
  const box=$('#predep'); box.innerHTML='';
  const m=predepMissing(); if(!m) return;
  const missAll=m.all, missAny=m.any, req={note:m.note};

  const d=el('div','bigerr');
  d.appendChild(el('h3','', 'You are not yet eligible to go on exchange'));
  const p1=el('p'); p1.innerHTML=req.note+
    ': these must all be <b>completed before you leave</b>. Add them to either box above if you\'ve '+
    'taken them or plan to — otherwise you cannot be approved for this term.';
  d.appendChild(p1);
  const ul=el('ul');
  missAll.forEach(c=>{const li=el('li');li.innerHTML='<code>'+pretty(c)+'</code> — not in your lists';ul.appendChild(li)});
  if(missAny){
    const li=el('li');
    li.innerHTML='<b>'+missAny.need+' more</b> from: '+missAny.of.map(c=>'<code>'+pretty(c)+'</code>').join(', ');
    ul.appendChild(li);
  }
  d.appendChild(ul);
  box.appendChild(d);
}

/* ---------- eligibility gates ---------- */
function gates(){
  const p=prog(),box=$('#gates');box.innerHTML='';if(!p)return;
  const cgRaw=parseFloat($('#cgpa').value);
  const g=GATE[p.f[0]],yr=$('#year').value,cg=Math.min(cgRaw,4.0),fin=$('#finalTerm').checked;
  const out=[];
  if(p.f.includes('noexch'))out.push(['stop',FACNOTE.noexch.t,FACNOTE.noexch.b]);
  if(p.f.includes('nomus'))out.push(['stop',FACNOTE.nomus.t,FACNOTE.nomus.b]);
  if(p.f.includes('law'))out.push(['stop',FACNOTE.law.t,FACNOTE.law.b]);
  const ac=$('#admcat');
  if(p.f.includes('law')&&ac&&ac.value!=='regular')
    out.push(['stop','Not eligible: admission category',
      'Advanced standing and transfer students are categorically ineligible for exchange or study away at the Faculty of Law. This is a block on student class, not on any course.']);
  if(p.f.includes('mgmt')&&$('#cegep')&&$('#cegep').checked)
    out.push(['warn','HEC Paris will reject your application',
      'HEC Paris does not accept applicants who completed a French Baccalauréat or attended CEGEP in Quebec. It has been removed from your destination list.']);
  if(g&&!isNaN(cg)&&cg<g.cgpa)
    out.push([g.soft?'warn':'stop',`CGPA below ${g.cgpa.toFixed(2)}`,
      g.soft?`Your faculty asks for ${g.cgpa.toFixed(2)}; students below it with documented circumstances may still be considered.`
            :`Your faculty requires a minimum CGPA of ${g.cgpa.toFixed(2)} at the time of application.`]);
  if(p.f.includes('mgmt')&&yr==='U0')
    out.push(['stop','U0 students cannot apply','Desautels does not accept applications from U0 students. Apply in U1; U2 is ideal.']);
  if(p.f.includes('music')&&yr&&!['U2','U3'].includes(yr))
    out.push(['stop','Music exchange is U2–U3 only',
      'Schulich requires students to be entering U2 or U3 at the time of exchange. Other year levels are not eligible.']);
  if(p.f.includes('ece')&&fin)
    out.push(['stop','ECE final-semester ban','Electrical, Computer and Software Engineering students may not go on exchange in their final semester. This is categorical.']);
  if((p.f.includes('sci')||p.f.includes('arts'))&&fin)
    out.push(['warn','Graduation will be delayed','Studying elsewhere in your final term makes you ineligible to graduate that term; graduation moves to the next one.']);
  out.forEach(([k,t,b])=>{const d=el('div','alert '+k);d.appendChild(el('b',null,t));
    d.appendChild(document.createTextNode(b));box.appendChild(d)});
}

/* ---------- prerequisite evaluation ---------- */
function ev(t,set){
  if(t===null||t===undefined) return true;
  if(typeof t==='string') return set.has(N(t));
  return t.op==='and' ? t.kids.every(k=>ev(k,set)) : t.kids.some(k=>ev(k,set));
}
function missingFrom(t,set){
  if(t===null||t===undefined) return [];
  if(typeof t==='string') return set.has(N(t))?[]:[N(t)];
  if(t.op==='and'){let o=[];t.kids.forEach(k=>o=o.concat(missingFrom(k,set)));return o}
  return t.kids.some(k=>ev(k,set))?[]:[t.kids.filter(k=>typeof k==='string').map(N)];
}
function flatten(t,out){
  if(t===null||t===undefined)return;
  if(typeof t==='string'){out.push(N(t));return}
  t.kids.forEach(k=>flatten(k,out));
}

/* Status is three-state: A approved, N not approved, E expired.
   Expired is NOT a dead end - the previous approval simply lapsed and
   a reassessment can be requested, usually successfully. Only N is
   permanent. Lumping the two together would wrongly discard options. */
function universalBlock(r){
  if(r.st==='N') return "Assessed Not Equivalent — permanently blocked, cannot be reconsidered";
  if(r.gr)       return "Graduate-only course (600+) — not accepted for transfer";
  if(r.rs)       return "Research or thesis project — cannot be taken on exchange";
  if(r.mt2)      return "Multi-term course (D1/D2, N1/N2) — halves cannot be split or mapped";
  return null;
}
/* Credits: use the real value where the catalogue supplied one,
   otherwise assume the McGill standard of 3 and say so. */
const CREDIT_DEFAULT = 3;
const creditsOf = r => (r.cr != null ? r.cr : CREDIT_DEFAULT);
const creditsKnown = r => r.cr != null;

/* OPEN | CONDITIONAL | LOCKED */
function assess(r){
  const sc=scopes();
  let block=universalBlock(r);
  if(!block) for(const b of BLOCK)
    if(sc.includes(b.scope)&&b.test(N(r.mc))){block=b.why;break}
  if(!block&&sc.includes('hon')&&r.lvl>=400&&r.rs)
    block="Honours research course — cannot be replicated abroad";
  const warns=[];
  for(const w of WARN) if(sc.includes(w.scope)&&w.test(N(r.mc))) warns.push(w.why);

  const expired = !block && r.st==='E';
  const already=passed.has(N(r.mc))||planned.has(N(r.mc));
  const both=new Set([...passed,...planned]);
  const openNow=ev(r.tree,passed);
  const openLater=ev(r.tree,both);

  let state='open', needs=[];
  if(block||already) state='blocked';
  else if(openNow) state='open';
  else if(openLater){
    state='cond';
    const all=[];flatten(r.tree,all);
    needs=all.filter(c=>planned.has(c)&&!passed.has(c));
  } else {
    state='locked';
    needs=missingFrom(r.tree,both).map(x=>Array.isArray(x)?x.join(' or '):x);
  }
  if(expired && (state==='open'||state==='cond')) state='expired';
  return {block,warns,already,state,needs,expired,
          ok:state==='open'||state==='cond'||state==='expired'};
}

/* ---------- navigation ---------- */
function goto(n){
  if(n>1&&!prog()){alert('Choose your degree program first.');return}
  [1,2,3,4].forEach(i=>{$('#s'+i).classList.toggle('hide',i!==n);
    $('#tab'+i).classList.toggle('on',i===n)});
  if(n===3)renderUnis(); if(n===4)renderCourses();
  window.scrollTo({top:0,behavior:'smooth'});
}

/* ---------- universities ---------- */
function renderUnis(){
  if(!READY)return; const p=prog(); if(!p)return;

  // A student who skipped the step-2 warning must be stopped here too.
  const bb=$('#blockBox'); bb.innerHTML='';
  const pm=predepMissing();
  if(pm){
    const d=el('div','bigerr');
    d.appendChild(el('h3',null,'You cannot go on exchange with these courses'));
    const q=el('p');
    q.innerHTML=pm.note+': every one of these must be <b>finished before you leave</b>. '+
      'Based on what you entered in step 2, you would not be approved for this term.';
    d.appendChild(q);
    const ul=el('ul');
    pm.all.forEach(c=>{const li=el('li');
      li.innerHTML='<code>'+pretty(c)+'</code> — not in your passed or planned lists';ul.appendChild(li)});
    if(pm.any){const li=el('li');
      li.innerHTML='<b>'+pm.any.need+' more</b> from: '+pm.any.of.map(c=>'<code>'+pretty(c)+'</code>').join(', ');
      ul.appendChild(li)}
    d.appendChild(ul);
    const q2=el('p'); q2.style.marginTop='12px';
    q2.innerHTML='Go back to <b>step 2</b> and add them if you\'ve taken them or plan to before '+
      'departure. Otherwise speak to your departmental adviser about a later term.';
    d.appendChild(q2);
    bb.appendChild(d);
    $('#uniList').innerHTML=''; $('#uniSum').innerHTML=''; $('#ruleBox').innerHTML='';
    return;
  }

  const box=$('#ruleBox');box.innerHTML='';
  p.f.forEach(f=>{const n=FACNOTE[f];if(!n)return;
    const d=el('div','alert '+n.k);d.appendChild(el('b',null,n.t));
    d.appendChild(document.createTextNode(n.b));box.appendChild(d)});

  UNENFORCED.forEach(n=>{ if(!n.when(p)) return;
    const d=el('div','alert info'); d.appendChild(el('b',null,n.t));
    d.appendChild(document.createTextNode(n.b)); box.appendChild(d); });

  const fb=facultyBlocked();
  if(fb){
    const d=el('div','bigerr');
    d.appendChild(el('h3',null,fb.t));
    const q=el('p');q.textContent=fb.b;d.appendChild(q);
    bb.appendChild(d);
    $('#uniList').innerHTML='';$('#uniSum').innerHTML='';return}

  const cty=$('#fcountry').value,sj=$('#fsubj').value,
        onlyEl=$('#onlyEligible').checked,useCond=$('#countCond').checked;
  const sc=scopes();
  // destinations excluded outright for this student (§3.6.9)
  const banned=new Map();
  DESTRULES.forEach(rule=>{
    if(!sc.includes(rule.scope))return;
    const anyCart=[...CART.values()].reduce((m,s)=>{s.forEach((v,k)=>m.set(k,v));return m},new Map());
    if(rule.when(anyCart)) banned.set(rule.match,rule.why);
  });
  const isBanned=u=>{for(const [m,why] of banned) if(m(u)) return why; return null};
  const map=new Map();
  DATA.forEach(r=>{
    if(cty&&r.co!==cty)return; if(sj&&r.sub!==sj)return;
    const a=assess(r);
    if(a.block||a.already)return;
    if(onlyEl&&a.state==='locked')return;
    if(!useCond&&a.state==='cond')return;
    if(isBanned(r.in))return;
    if(!map.has(r.in))map.set(r.in,{n:r.in,co:r.co,rows:[],rel:0,cond:0});
    const g=map.get(r.in); g.rows.push(r);
    if(relevance(r.sub)>=2)g.rel++;
    if(a.state==='cond')g.cond++;
  });
  const list=[...map.values()].sort((a,b)=>b.rel-a.rel||b.rows.length-a.rows.length||a.n.localeCompare(b.n));

  banned.forEach(why=>{
    const a=el('div','alert warn');
    a.appendChild(el('b',null,'A destination was removed from your results'));
    a.appendChild(document.createTextNode(why));
    box.appendChild(a);
  });

  const maj=major();
  $('#uniSum').innerHTML=list.length
    ?(maj?`<b>${list.length}</b> universities have courses open to you — ranked by how many sit in or near <b>${subjLabel(maj)}</b>.`
         :`<b>${list.length}</b> universities have courses open to you. Pick your field in step 1 to rank by relevance.`)
    :'';
  const out=$('#uniList');out.innerHTML='';
  if(!list.length){
    out.innerHTML='<div class="empty"><div class="big">No matches with these filters.</div>'+
      'Try “Anywhere”, clear the subject filter, or allow conditional courses. '+
      'A university with no entry just means nobody has asked yet.</div>';return}

  const maxN=list[0].rel||list[0].rows.length||1;
  list.slice(0,120).forEach((u,i)=>{
    const d=el('div','uni');d.setAttribute('role','button');d.tabIndex=0;
    const open=()=>{curUni=u.n;goto(4)};
    d.onclick=open; d.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}};
    d.appendChild(el('div','rank',String(i+1)));
    const mid=el('div');
    mid.appendChild(el('div','uname',u.n));
    mid.appendChild(el('div','ucty',u.co||'—'));
    const bar=el('div','ubar'),fill=document.createElement('i');
    fill.style.width=(100*(u.rel||u.rows.length)/maxN).toFixed(1)+'%';
    fill.style.animationDelay=Math.min(i,20)*0.025+'s';
    bar.appendChild(fill);mid.appendChild(bar);
    d.appendChild(mid);
    const c=el('div','ucount');
    c.appendChild(el('div','n',String(maj?u.rel:u.rows.length)));
    c.appendChild(el('div','l',maj?'in your field':'courses'));
    const extras=[];
    if(maj&&u.rows.length>u.rel)extras.push('+'+(u.rows.length-u.rel)+' other');
    if(u.cond)extras.push(u.cond+' conditional');
    if(extras.length)c.appendChild(el('div','usub',extras.join(' · ')));
    d.appendChild(c);
    out.appendChild(d);
  });
}

/* ============================================================
   Course selection cart + transfer-credit caps
   Credit values are NOT in McGill's equivalency data, so we assume
   the standard 3 credits per course and say so in the UI.
   ============================================================ */
const CART = new Map();                 // university -> Map(key -> row)
const cartFor = u => { if(!CART.has(u)) CART.set(u,new Map()); return CART.get(u) };
const keyOf = r => r.mc+'|'+r.hc+'|'+r.in;

/* Caps in CREDITS, from the faculty rules. null = no stated cap. */
function capsFor(){
  const p=prog(); if(!p) return {};
  const hon = $('#honours') && $('#honours').checked;
  const ib  = $('#ibConc') && $('#ibConc').checked;
  if(p.f.includes('mgmt')) return {core:9, major:12, minor:ib?null:6, topics:6, term:15, termExact:15,
    src:'Desautels: Core 9 · Major 12 · Concentration/Minor 6 · Electives unlimited · Topics 6',
    ibNote: ib};
  if(p.f.includes('arts'))  return {major:hon?21:12, minor:6, outside:12,
    src:'Arts: Major 12 · Honours 21 · Joint Honours 12 · Minor 6 · max 12 credits from outside Arts and Science'};
  if(p.f.includes('sci'))   return {minor:6, term:15, termMin:12, outside:12,
    src:'Science: max 15 transfer credits per term, study plan of 4–5 courses required, max 12 credits from outside Arts and Science'};
  if(p.f.includes('eng'))   return {minor:6, term:15,
    src:'Engineering: Minor 6 credits · exactly 50% of the program must be completed at McGill'};
  if(p.f.includes('faes'))  return {term:15,
    src:'FAES: 60 credits at McGill (72 Bioresource) AND two-thirds at Macdonald Campus'};
  if(p.f.includes('educ'))  return {src:'Education: 60 credits at McGill; no two-thirds program-residency rule is published'};
  return {term:15, src:''};
}

/* Subjects that count as "outside Arts and Science" (§3.2.7, §3.7.8) */
const INSIDE_AS = new Set(M_ARTS.concat(M_SCI).concat(['SWRK','WCOM','LSCI','MATH','STAT']));

/* Which cap bucket a chosen course falls into */
function category(r){
  const p=prog();
  if(p&&p.f.includes('mgmt')&&r.sub==='MGCR') return 'core';
  if(major()&&r.sub===major()) return 'major';
  if(minorV()&&r.sub===minorV()) return 'minor';
  return 'elective';
}
const isTopics = r => /\btopics\b/i.test(r.mt||'');
const isOutsideAS = r => !INSIDE_AS.has(r.sub);
const CATNAME={core:'Management Core',major:'Major',minor:'Minor / Concentration',elective:'Elective'};

function renderCart(){
  const box=$('#cart'); box.innerHTML='';
  if(!curUni) return;
  const sel=cartFor(curUni);
  if(!sel.size) return;

  const caps=capsFor();
  const byCat={};
  [...sel.values()].forEach(r=>{const c=category(r);byCat[c]=(byCat[c]||0)+creditsOf(r)});
  const totalCr=[...sel.values()].reduce((a,r)=>a+creditsOf(r),0);
  const anyAssumed=[...sel.values()].some(r=>!creditsKnown(r));

  const d=el('div','cart');
  d.appendChild(el('h3',null,'Your selection at '+curUni));
  d.appendChild(el('div','tot',sel.size+' course'+(sel.size!==1?'s':'')+
    (anyAssumed?' \u2248 ':' = ')+totalCr+' credits'+(anyAssumed?' (3 assumed where the catalogue gave no value)':'')));

  const caprow=el('div','caps');
  const problems=[];

  const show=(k,label,cap)=>{
    const cr=byCat[k]||0; if(!cr && cap==null) return;
    const n=Math.round(cr/CREDIT_DEFAULT);
    const over = cap!=null && cr>cap;
    if(over) problems.push({label,cr,cap,n});
    const c=el('div','cap'+(over?' over':''));
    c.appendChild(el('div','k',label));
    const v=el('div','v',cr+(cap!=null?' / '+cap:'')); 
    if(cap!=null) v.appendChild(el('span','m',' cr'));
    c.appendChild(v);
    caprow.appendChild(c);
  };
  show('core','Management Core',caps.core!=null?caps.core:null);
  show('major','Major',caps.major!=null?caps.major:null);
  show('minor','Minor / Concentration',caps.minor!=null?caps.minor:null);
  show('elective','Electives',null);

  // §3.6.8 generic "Topics in ..." cap
  if(caps.topics!=null){
    const rs=[...sel.values()].filter(isTopics), n=rs.length, cr=rs.reduce((a,r)=>a+creditsOf(r),0);
    if(n){
      const over=cr>caps.topics;
      if(over)problems.push({label:'Topics courses',cr,cap:caps.topics,n});
      const c=el('div','cap'+(over?' over':''));
      c.appendChild(el('div','k','Topics courses'));
      const v=el('div','v',cr+' / '+caps.topics);v.appendChild(el('span','m',' cr'));
      c.appendChild(v);caprow.appendChild(c);
    }
  }
  // §3.2.7 / §3.7.8 max credits from outside Arts and Science
  if(caps.outside!=null){
    const rs=[...sel.values()].filter(isOutsideAS), n=rs.length, cr=rs.reduce((a,r)=>a+creditsOf(r),0);
    if(n){
      const over=cr>caps.outside;
      if(over)problems.push({label:'Outside Arts and Science',cr,cap:caps.outside,n});
      const c=el('div','cap'+(over?' over':''));
      c.appendChild(el('div','k','Outside Arts & Sci'));
      const v=el('div','v',cr+' / '+caps.outside);v.appendChild(el('span','m',' cr'));
      c.appendChild(v);caprow.appendChild(c);
    }
  }

  if(caps.term!=null){
    const over=totalCr>caps.term;
    if(over)problems.push({label:'Term total',cr:totalCr,cap:caps.term,n:sel.size});
    const c=el('div','cap'+(over?' over':''));
    c.appendChild(el('div','k','Term total'));
    const v=el('div','v',totalCr+' / '+caps.term); v.appendChild(el('span','m',' cr'));
    c.appendChild(v); caprow.appendChild(c);
  }
  d.appendChild(caprow);

  problems.forEach(p=>{
    const a=el('div','alert stop'); a.style.marginTop='13px';
    a.appendChild(el('b',null,'Over the '+p.label.toLowerCase()+' limit'));
    a.appendChild(document.createTextNode(
      'You\'ve chosen '+p.n+' course'+(p.n!==1?'s':'')+' ≈ '+p.cr+' credits, but only '+p.cap+
      ' credits may transfer in this category. '+
      (caps.src?caps.src+'. ':'')+
      'Remove '+Math.ceil((p.cr-p.cap)/CREDIT_DEFAULT)+' course'+
      (Math.ceil((p.cr-p.cap)/CREDIT_DEFAULT)!==1?'s':'')+' or check with your adviser.'));
    d.appendChild(a);
  });

  // §3.6.3 Desautels must map exactly 15 credits; §3.7.13 Science needs 12-15
  if(caps.termExact!=null && totalCr!==caps.termExact){
    const a=el('div','alert '+(totalCr<caps.termExact?'warn':'stop'));a.style.marginTop='13px';
    a.appendChild(el('b',null,totalCr<caps.termExact?'Not yet a valid Desautels plan':'Over the term load'));
    a.appendChild(document.createTextNode(
      'Desautels requires exchange students to map exactly '+caps.termExact+
      ' McGill credits per term — a full load — regardless of how the host weights its courses. '+
      'You currently have '+totalCr+'. '+
      (totalCr<caps.termExact?'Add '+Math.ceil((caps.termExact-totalCr)/CREDIT_DEFAULT)+' more course(s).':'')));
    d.appendChild(a);
  }
  if(caps.termMin!=null && totalCr<caps.termMin){
    const a=el('div','alert warn');a.style.marginTop='13px';
    a.appendChild(el('b',null,'Study plan is too small'));
    a.appendChild(document.createTextNode(
      'Science requires a full-time study plan of 4–5 courses ('+caps.termMin+'–15 credits) before an '+
      'exchange can be approved. A single-course plan is not a valid application. You have '+
      sel.size+' course'+(sel.size!==1?'s':'')+'.'));
    d.appendChild(a);
  }
  if(caps.ibNote){
    const a=el('div','alert info');a.style.marginTop='13px';
    a.appendChild(el('b',null,'International Business exception applies'));
    a.appendChild(document.createTextNode(
      'The 6-credit concentration cap is waived for International Business, since international '+
      'exposure is the point of the concentration.'));
    d.appendChild(a);
  }

  const list=el('div','cartlist');
  [...sel.values()].sort((a,b)=>a.mc.localeCompare(b.mc)).forEach(r=>{
    const ch=el('span','chip');
    ch.appendChild(el('span',null,pretty(r.mc)));
    const x=el('button',null,'×'); x.setAttribute('aria-label','Remove '+pretty(r.mc));
    x.onclick=()=>{sel.delete(keyOf(r));renderCourses()};
    ch.appendChild(x); list.appendChild(ch);
  });
  d.appendChild(list);
  box.appendChild(d);
}

/* ============================================================
   Step 3, mode B: find universities offering a package of courses
   ============================================================ */
const PKG = new Set();

function s3mode(m){
  $('#s3a').classList.toggle('on',m==='rank');
  $('#s3b').classList.toggle('on',m==='course');
  $('#s3rank').classList.toggle('hide',m!=='rank');
  $('#s3course').classList.toggle('hide',m!=='course');
  if(m==='course') renderPkg();
}

function wirePkg(){
  const inp=$('#pkg'), sug=$('#sugPkg'), err=$('#errPkg'); let hl=-1;
  const close=()=>{sug.classList.remove('show');hl=-1};
  inp.addEventListener('input',()=>{
    err.innerHTML='';
    const raw=inp.value.toUpperCase(), q=N(inp.value);
    if(q.length<3){close();return}
    const sm=raw.match(/^([A-Z]{3,4})\s/);
    let hits;
    if(sm){const su=sm[1],rest=q.slice(su.length);
      hits=[...VALID].filter(c=>c.startsWith(su)&&c.slice(su.length).startsWith(rest)).sort();}
    else hits=[...VALID].filter(c=>c.startsWith(q)).sort().slice(0,10);
    if(!hits.length){close();return}
    sug.innerHTML='';
    hits.forEach(c=>{const d=el('div');d.appendChild(el('span',null,pretty(c)));
      if(TITLES[c])d.appendChild(el('span','t',TITLES[c]));
      d.onclick=()=>addPkg(c);sug.appendChild(d)});
    sug.classList.add('show');
  });
  inp.addEventListener('keydown',e=>{
    const items=[...sug.querySelectorAll('div')];
    if(e.key==='ArrowDown'&&items.length){e.preventDefault();hl=Math.min(hl+1,items.length-1)}
    else if(e.key==='ArrowUp'&&items.length){e.preventDefault();hl=Math.max(hl-1,0)}
    else if(e.key==='Escape'){close();return}
    else if(e.key==='Enter'){e.preventDefault();
      if(hl>=0&&items[hl]){items[hl].click();return} addPkg(N(inp.value));return}
    else return;
    items.forEach((x,i)=>x.classList.toggle('hl',i===hl));
  });
  document.addEventListener('click',e=>{if(!e.target.closest('#s3course .inpwrap'))close()});
  function addPkg(code){
    if(!code)return;
    if(!VALID.has(code)){
      err.innerHTML='';err.appendChild(el('div','err',pretty(code)+' isn\'t a McGill course code.'));return;}
    PKG.add(code); inp.value=''; close(); renderPkg();
  }
}

function renderPkg(){
  const box=$('#chipsPkg'); box.innerHTML='';
  [...PKG].sort().forEach(c=>{
    const ch=el('span','chip'); ch.appendChild(el('span',null,pretty(c)));
    const x=el('button',null,'\u00d7'); x.onclick=()=>{PKG.delete(c);renderPkg()};
    ch.appendChild(x); box.appendChild(ch);
  });
  const sum=$('#pkgSum'), out=$('#pkgList'); out.innerHTML='';
  if(!PKG.size){sum.innerHTML='';out.innerHTML=
    '<div class="empty"><div class="big">Add a course to begin.</div>'+
    'Enter one course to see everywhere it transfers, or several to find a single university '+
    'that covers them all.</div>';return}

  // for each university, which of the wanted courses does it offer (approved only)?
  const want=[...PKG];
  const uni=new Map();
  DATA.forEach(r=>{
    if(r.st!=='A')return;
    const mc=N(r.mc);
    if(!want.includes(mc))return;
    if(!uni.has(r.in))uni.set(r.in,{n:r.in,co:r.co,got:new Set(),rows:{}});
    const u=uni.get(r.in); u.got.add(mc);
    (u.rows[mc]=u.rows[mc]||[]).push(r);
  });
  const list=[...uni.values()].sort((a,b)=>b.got.size-a.got.size||a.n.localeCompare(b.n));
  const full=list.filter(u=>u.got.size===want.length);

  sum.innerHTML = want.length===1
    ? `<b>${list.length}</b> universities offer an equivalent for ${pretty(want[0])}.`
    : `<b>${full.length}</b> universit${full.length===1?'y offers':'ies offer'} all ${want.length} courses`+
      (list.length>full.length?` · ${list.length-full.length} more offer some`:'')+'.';

  if(!list.length){out.innerHTML=
    '<div class="empty"><div class="big">No university has an approved equivalent.</div>'+
    'Nobody has had these assessed yet — that\'s not the same as impossible. A paper equivalency '+
    'request through your adviser may still work.</div>';return}

  const rows=el('div','rows');
  list.forEach(u=>{
    const row=el('div','pkgrow');
    const L=el('div');
    L.appendChild(el('div','nm',u.n));
    L.appendChild(el('div','cy',u.co||''));
    row.appendChild(L);
    const R=el('div','co');
    want.forEach((c,i)=>{
      const has=u.got.has(c);
      const span=el('span',null,(i?' · ':'')+pretty(c));
      if(has){const b=el('b',null,pretty(c)); if(i)R.appendChild(document.createTextNode(' · ')); R.appendChild(b);}
      else{const g=el('span',null,pretty(c));g.style.opacity=.35;
        if(i)R.appendChild(document.createTextNode(' · '));R.appendChild(g);}
    });
    row.appendChild(R);
    rows.appendChild(row);
  });
  out.appendChild(rows);
}

/* ---------- course list ---------- */
function placeholder(code){
  const m=String(code).toUpperCase().match(/^([A-Z]+)\s?(\d)XX$/);
  if(m) return `counts as any ${m[2]}00-level ${m[1]} course`;
  if(/^([A-Z]+)\s?XXX$/.test(String(code).toUpperCase()))
    return `counts as general ${String(code).toUpperCase().replace(/XXX$/,'')} credit`;
  return null;
}

function renderCourses(){
  if(!curUni){goto(3);return}
  const showAll=$('#showBlocked').checked, sj=$('#fsubj').value;
  const rows=DATA.filter(r=>r.in===curUni&&(!sj||r.sub===sj));
  const head=$('#uniHead');head.innerHTML='';
  head.appendChild(el('div','uhead-c',rows[0]?(rows[0].co||''):''));
  head.appendChild(el('div','uhead',curUni));
  DESTNOTE.forEach(n=>{
    if(!n.match(curUni))return;
    const a=el('div','alert warn');a.style.marginTop='14px';
    a.appendChild(el('b',null,n.t));
    a.appendChild(document.createTextNode(n.b));
    head.appendChild(a);
  });

  const scored=rows.map(r=>({r,a:assess(r)}));
  const open=scored.filter(x=>x.a.state==='open');
  const cond=scored.filter(x=>x.a.state==='cond');
  const exp=scored.filter(x=>x.a.state==='expired');
  const rest=scored.filter(x=>!['open','cond','expired'].includes(x.a.state));
  const show=showAll?scored:open.concat(cond).concat(exp);

  $('#cSum').innerHTML=`<b>${open.length}</b> open now`+
    (cond.length?` · <b>${cond.length}</b> conditional`:'')+
    (exp.length?` · <b>${exp.length}</b> expired but renewable`:'')+
    (rest.length?` · ${rest.length} blocked, done, or missing prerequisites`:'');

  renderCart();
  const out=$('#cList');out.innerHTML='';
  if(!show.length){
    out.innerHTML='<div class="empty"><div class="big">Nothing open here.</div>'+
      'Tick “show blocked” to see why, or go back and choose another university.</div>';return}

  show.sort((x,y)=>{
    const o={open:0,cond:1,expired:2,locked:3,blocked:4};
    return o[x.a.state]-o[y.a.state]||x.r.mc.localeCompare(y.r.mc)});

  const maj=major();
  const TIERS=maj?[
    {t:3,label:'In your field',why:subjLabel(maj)},
    {t:2,label:'Related to your field',why:'shares prerequisites or the same faculty'},
    {t:1,label:'Everything else',why:'usually elective credit'}
  ]:[{t:0,label:'',why:''}];

  TIERS.forEach(tier=>{
    const grp=maj?show.filter(x=>relevance(x.r.sub)===tier.t):show;
    if(!grp.length)return;
    if(maj){
      const hd=el('div','ghdr'+(tier.t===3?' t3':''));
      hd.appendChild(el('h3',null,tier.label));
      hd.appendChild(el('span','c',String(grp.length)));
      hd.appendChild(el('span','rule'));
      hd.appendChild(el('span','why',tier.why));
      out.appendChild(hd);
    }
    const box=el('div','rows');
    grp.forEach(({r,a})=>{
      const sel=cartFor(curUni), k=keyOf(r), chosen=sel.has(k);
      const row=el('div','row'+(a.ok?'':' blocked')+(chosen?' sel':''));
      const pick=el('button','pick');
      pick.type='button';
      pick.setAttribute('aria-pressed',chosen?'true':'false');
      pick.setAttribute('aria-label',(chosen?'Remove ':'Add ')+pretty(r.mc)+' to your selection');
      pick.disabled=!a.ok;
      pick.title=a.ok?(chosen?'Remove from your selection':'Add to your selection')
                     :'Not available to you';
      pick.onclick=ev=>{ev.stopPropagation();
        if(sel.has(k)) sel.delete(k); else sel.set(k,r);
        renderCourses();};
      row.appendChild(pick);
      const L=el('div');
      const cl=el('div','ccode mono',pretty(r.mc));
      const cb=el('span','crbadge'+(creditsKnown(r)?'':' assumed'),
        creditsOf(r)+' cr'+(creditsKnown(r)?'':'?'));
      cb.title=creditsKnown(r)?'Credit value from the McGill Course Catalogue'
                              :'No credit value published \u2014 3 assumed';
      cl.appendChild(cb);
      const gen=placeholder(r.mc);
      if(gen)cl.appendChild(el('span','pill','generic'));
      if(a.state==='cond')cl.appendChild(el('span','pill','*'));
      L.appendChild(cl);
      if(gen)L.appendChild(el('div','tag gen',gen));
      if(r.cmp)L.appendChild(el('div','tag joint',
        '⚭ requires the full course combination shown — not a single-course match'));
      if(r.jt)L.appendChild(el('div','tag joint',
        '500-level: joint undergraduate/graduate, open to U3 students'));
      if(a.state==='expired')L.appendChild(el('div','tag exp',
        '↻ approval lapsed — request a reassessment in the equivalency database; these are usually renewed'));
      if(a.block)L.appendChild(el('div','tag blk','⊘ '+a.block));
      else if(a.already)L.appendChild(el('div','tag blk','already in your lists'));
      else if(a.state==='cond')
        L.appendChild(el('div','tag cond','* only if you pass '+a.needs.map(pretty).join(' and ')+' first'));
      else if(a.state==='locked')
        L.appendChild(el('div','tag miss','needs '+a.needs.map(x=>pretty(x)).join(', ')));
      a.warns.forEach(w=>L.appendChild(el('div','tag wrn','⚠ '+w)));
      row.appendChild(L);
      row.appendChild(el('div','ctitle',r.mt||''));
      row.appendChild(el('div','arw','→'));
      const R=el('div');
      R.style.cursor='pointer';
      R.title='Click to search for this course on the host university\'s website';
      R.onclick=ev=>{ev.stopPropagation();
        const q=encodeURIComponent(
          (r.ht||r.hc||'').trim()+' '+r.in.replace(/\s*\(.*?\)\s*/g,'').trim()+' course');
        window.open('https://www.google.com/search?q='+q,'_blank','noopener');};
      R.appendChild(el('div','hcode mono',r.hc||'—'));
      R.appendChild(el('div','htitle'+(r.ht?' clicksearch':''),r.ht||''));
      row.appendChild(R);
      const v=a.state==='open'?'v-ok':a.state==='cond'?'v-cd':
              a.state==='expired'?'v-ex':'v-no';
      const lbl=a.block?'Blocked':a.already?'Done':a.state==='cond'?'Conditional':
                a.state==='expired'?'Expired':a.state==='locked'?'Locked':'Open';
      row.appendChild(el('div','verdict '+v,lbl));
      box.appendChild(row);
    });
    out.appendChild(box);
  });
}
"""

JS = (JS.replace('__REL__', json.dumps(REL, separators=(',', ':'), sort_keys=True))
        .replace('__TITLES__', json.dumps(TITLES, ensure_ascii=False, separators=(',', ':')))
        .replace('__CODES__', json.dumps(CODES)))

LOADER = """
fetch('planner_data.json').then(r=>{if(!r.ok)throw 0;return r.json()})
 .then(d=>{DATA=d;READY=true;boot()})
 .catch(()=>{document.getElementById('uniList').innerHTML=
   '<div class="empty"><div class="big">Couldn\\'t load the data.</div>Make sure '+
   '<span class="mono">planner_data.json</span> sits beside this file and you\\'re opening it '+
   'through a web server, not a file:// path.</div>'});
"""

html = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>McGill Exchange Planner</title>\n" + CSS + "\n</head>\n<body>\n"
        + BODY + "\n<script>\n" + JS + LOADER + "\n</script>\n</body>\n</html>\n")

open('exchange.html', 'w', encoding='utf-8').write(html)
print('built', round(len(html)/1024, 1), 'KB')
