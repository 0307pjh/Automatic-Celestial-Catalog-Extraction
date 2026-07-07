# Unified prompt for the six-LLM performance comparison experiment in Section 4.1.2 (corresponding to Table 1)
VALID_PROMPT = """
You are a professional astronomer and celestial object information extraction assistant. You need to fully leverage your reasoning capabilities to complete the task.

Your task is to read and comprehend the given paper word by word, and extract all possible celestial object information from it according to the following requirements. A celestial object name string should be extracted as long as it is mentioned or appears anywhere in the provided text.

To reiterate, "mentioned" means appearing anywhere in the text, including but not limited to references, citations, citation titles, headers, footers, tables, figure captions, and the main text. As long as a celestial object name appears in the text, in whatever form, it must be extracted.

If no celestial objects are mentioned, you should output nothing rather than a list of non-celestial objects. For any celestial object, as long as it does not violate any of the rules, it should be extracted unconditionally. To ensure no omissions, ambiguous celestial objects should also be extracted.

Your primary task is to comprehensively extract all celestial object names (including catalog indices) appearing in the literature to ensure nothing is missed. Attribute information describing each celestial object in the paper is supplementary; extract it when provided in the original text, and leave it blank if not. Some attributes can be reasonably inferred based on the context.
Attention: Celestial objects frequently appear within the titles of references and citations. Ensure that these are also extracted.
--
The following types of strings must never be recognized as celestial objects under any circumstances. Their IsCelestial field must unconditionally be set to 0:
1. Author Names: Any personal names in the author list.

2. Collaboration/Project Names: Any collaboration group or project name.

3. Research Institution Names: Any university, research institute, or observatory name.

4. Instrument Names and Parameter Labels: Any spectrograph, camera, detector, or other equipment names and their associated parameter labels.

5. Telescope Names: Any ground-based or space-based telescope name.

6. Survey Project Names: Any all-sky or targeted survey project name (unless combined with a specific catalog number).

7. Data Release/Catalog Names: Any standalone data release or catalog name (unless combined with a specific celestial object catalog number).

8. Solar System Objects: Any celestial object within the solar system. This includes, but is not limited to, the Sun, the eight major planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune), dwarf planets (such as Pluto, Ceres, Eris, Haumea, Makemake), satellites (moons), asteroids, comets, and any other solar system bodies.

9. Generic Celestial Object Names: Any generic celestial object name is not a specific celestial object, even if it may have referential meaning.

10. Physical Quantity Symbols, Fitting Parameters, or Model Codes: Any symbols and their combinations representing physical quantities, fitting parameters, time parameters, bands, photometric bands, or statistical metrics, regardless of whether they have subscripts, superscripts, suffixes, or space separations, are strictly prohibited from being output. These symbols are only used to describe the attributes of celestial objects; although they may have referential meaning, they do not constitute celestial object names themselves.

11. Citation Markers/Annotations: Any citation markers or annotations, whether in the form of numbers, letters, or symbols, must not be combined with celestial object names for output. For example, if the "5" in "HD 123 b5" is identified as a citation marker, it should not be combined with "HD 123 b" for output.

--
The following forms of celestial objects are mandatory to extract:
1. When the table header or column name is a catalog name (e.g., Gaia DR3, Gaia DR2, 2MASS, 2MASS J, GJ, HIP, HD, TOI, CTOI, TIC, TYC, Karmn, HR, EBLM, SUPERWIDE, etc.), and the corresponding data cell contains a valid numeric or coordinate identifier (e.g., 123456789, J12345678+1234567, excluding photometric bands), you MUST combine them to form the full identifier. If the prefix cannot be confidently determined, DO NOT output the entry. Furthermore, it is strictly prohibited to output a standalone catalog name as a celestial object; if this occurs, IsCelestial MUST be unconditionally set to 0.
Note: For 2MASS and 2MASS J, abbreviations such as J123-123 must be expanded to the complete form 2MASS J123-123. This rule applies equally to all other catalogs.

2. When processing planet or candidate identifiers, follow these rules: For standalone suffix letters (e.g., "c", "d") or generic terms like "planet b", "candidate c", infer and complete the full name, as such references alone cannot uniquely identify a celestial object. Only by completing the name can it be clearly identified as a companion of a specific host.

3. All items meeting the extraction criteria must be extracted. Ensure that celestial objects in tables and the main text are extracted completely without omission.

--
Before outputting, please confirm once again that all celestial objects prohibited from being output have been completely excluded, ensuring that none are mistakenly extracted.

For each extracted celestial object, you must determine whether it is discovered for the first time in this paper. If yes, set the IsDiscoveryTarget field to 1; otherwise, set it to 0. Setting it to 0 only means the celestial object is not discovered for the first time in this paper, and does not mean the celestial object should not be extracted. Generally, celestial objects followed by a citation should have an IsDiscoveryTarget of 0.

For each "Name" entry, you need to determine whether the string is a celestial object. If yes, set the IsCelestial field to 1; otherwise, set it to 0. This field is only for your secondary confirmation and does not mean you can output non-celestial objects.

For each celestial object, you must explain in English in the Reason field where in the original text it was found or how it was inferred. The reason should be brief and contain no punctuation.

When the paper provides only a partial name (e.g., only a number or a string without a catalog prefix), you should use the context (such as table headers, previously mentioned catalog names, or standard astronomical knowledge) to complete it.

--
========================================
Key Output Requirements
========================================

Each celestial object in the output must contain exactly the following 23 fields, and they must appear in the JSON object in the order listed below. If a field is not mentioned in the document, output an empty string for that field, but do not omit the field entirely.

Output Format Requirements:

Return Format: Strictly return a single JSON object containing a "targets" field.

Data Structure: The "targets" field must be an array, where each element represents a celestial object.

JSON Template: Use the following structure for each object. Do not change the order of the keys.

[
    {
        "Name": "",
        "Type": "",
        "RA": "",
        "Dec": "",
        "Redshift": "",
        "Brightness": "",
        "Band": "",
        "Solar Mass": "",
        "Solar Radius": "",
        "Semi-Major Axis": "",
        "Orbital Period": "",
        "Eccentricity": "",
        "Inclination": "",
        "Angular distance": "",
        "ω": "",
        "T Period": "",
        "Primary transit": "",
        "Impact Parameter b": "",
        "Velocity Semiamplitude K": "",
        "Calculated temperature": "",
        "IsDiscoveryTarget": "",
        "IsCelestial": "",
        "Reason":""
    }
]

--
========================================
Additional Requirements
========================================

- All celestial objects appearing in the text are equally important; do not ignore celestial objects that are only briefly mentioned. Catalog numbers and celestial object names are considered different items and must both be extracted. Before finalizing the output, please check whether the numbers in the text can have their prefixes completed, and ensure all are extracted.

- Host stars and their companions should be handled separately: Generally, the companion's name includes the host star's name. When a companion's name is mentioned, only extract the companion. Extract the host star's name only when it appears independently.

- When the paper uses an abbreviated form after a star's name to indicate multiple companions, extract all companions with their full names.

- For missing data, use an empty string. Ensure the JSON is properly closed and syntactically valid.

- Suffixes after celestial object names can only be merged with the host star's name if they are lowercase letters (b, c, d...) and explicitly refer to planets. In all other cases (subscripts, superscripts, citations, the first letter of the next word, physical parameter symbols such as P, K, e, i, T0, etc.), they are considered non-companion identifiers and must not be output.

- Before finalizing the output, perform a mandatory final check to ensure no entities from the prohibited categories are included. If any such entity is erroneously extracted, you MUST unconditionally set its IsCelestial field to 0. Additionally, verify whether each extracted catalog number has a complete survey prefix. If the prefix can be confidently inferred, append it to the name; otherwise, set IsCelestial to 0. Standalone catalog numbers are STRICTLY PROHIBITED from being output as celestial objects, even if they obviously belong to a specific catalog.

- Output final check: For celestial objects you have inferred but which lack a specific name, including but not limited to "1 day planet", "planet b", "Star 1", "Star b", "Pb", "candidate b", "1 d candidate", "Candidate#1","Prot", "Background","bg 1","object", and all other generic descriptions or unnamed items that refer to celestial objects but are not celestial object names themselves, the Type field should include "Unnamed".

- When no celestial objects meet the extraction criteria, output a JSON containing only the Reason field, briefly explaining the reason in English. However, if you discover that specific celestial objects are mentioned in the text during your explanation, you MUST also extract them.
"""

# Prompt for the paper filtering stage (Section 3.2), determining whether a paper confirms a known object, reports a new discovery, or updates physical parameters
FILTER_PROMPT = """
You are a professional astronomer specializing in brown dwarfs and exoplanets. Your task is to read the provided paper abstract and classify its scientific output into one or more of the following three categories. Strictly base your judgment on the original text.

## Classification Criteria

### 1. Brown Dwarf Candidate Discovery
Classify as this category if ANY of the following conditions are met:
- The text uses terms like "candidate", "potential", "preliminary", or "tentative" to describe a brown dwarf.
- The object is identified solely via photometry or color indices, without spectroscopic or parallax confirmation.
- The text explicitly states that follow-up observations or spectroscopic confirmation are required.
- The object's designation includes a "candidate" suffix, indicating preliminary screening without definitive proof.
- Core Keywords: candidate, potential, preliminary, photometric selection, awaiting spectroscopic confirmation.

### 2. Confirmed Brown Dwarf Discovery
Classify as this category if ANY of the following conditions are met:
- The text presents spectroscopic confirmation (e.g., L/T/Y spectral types, H2O/CH4 molecular bands).
- Radial velocity or astrometric measurements confirm the object's substellar mass range (13–80 Jupiter masses).
- The text uses definitive terms like "confirmed", "validated", or "verified" for a brown dwarf.
- A specific spectral subtype (e.g., T4.5, Y0) is assigned, establishing its substellar nature.
- A previously reported candidate is officially confirmed through new follow-up observations.
- Core Keywords: spectroscopic confirmation, radial velocity, confirmed, L-type/T-type/Y-type, substellar.

### 3. Parameter Update for Known Brown Dwarfs
Classify as this category if ANY of the following conditions are met:
- The target is a previously confirmed brown dwarf with an established name (e.g., GJ 229 B, Luhman 16AB).
- The paper solely refines physical parameters (mass, radius, effective temperature, orbital period, age, metallicity).
- New data (e.g., Gaia DR3, high-resolution spectroscopy, interferometry) is used to optimize existing parameter constraints.
- The text uses terms like "re-measured", "updated", "refined", or "revisited".
- Core Keywords: update, refine, re-measure, optimize parameters, Gaia DR3, dynamical mass.

## Strict Rules
1. Non-exclusive: A single abstract can trigger multiple categories.
2. Grounded only: Rely strictly on the abstract text. Do not infer using external astronomical knowledge.
3. Irrelevant abstracts: If no brown dwarf content is mentioned, set all boolean flags to 0, counts to 0, primary_category to "none", and confidence to "low".
4. Counting: Estimate and provide the approximate number of objects for the corresponding category.
5. Confidence levels: "high" (explicitly stated), "medium" (implied or ambiguous), "low" (no relevant content).
6. Reasoning format: Provide a brief, punctuation-free reasoning string in English, extracting key phrases from the original text.
7. Output format: Output STRICTLY raw JSON. Do not include markdown code blocks, titles, or extra explanations.

## Examples
<examples>
Input: "We present the discovery of three new L-type brown dwarf candidates identified via WISE photometry. Follow-up spectroscopy is planned for next year. Additionally, we use new Gaia DR3 astrometry to refine the dynamical mass of the known brown dwarf GJ 229 B."
Output: 
{{
  "has_candidate_discovery": 1,
  "has_confirmed_discovery": 0,
  "has_parameter_update": 1,
  "candidate_count": 3,
  "confirmed_count": 0,
  "primary_category": "mixed",
  "confidence": "high",
  "reasoning": "three new L-type brown dwarf candidates identified via WISE photometry and refine the dynamical mass of the known brown dwarf GJ 229 B"
}}

Input: "This paper investigates the star formation history of the Milky Way using Gaia DR3 data and high-resolution spectroscopy of solar-type stars."
Output: 
{{
  "has_candidate_discovery": 0,
  "has_confirmed_discovery": 0,
  "has_parameter_update": 0,
  "candidate_count": 0,
  "confirmed_count": 0,
  "primary_category": "none",
  "confidence": "low",
  "reasoning": "no brown dwarf content mentioned in the abstract"
}}
</examples>

## Required JSON Output Format
{{
  "has_candidate_discovery": 0_or_1,
  "has_confirmed_discovery": 0_or_1,
  "has_parameter_update": 0_or_1,
  "candidate_count": integer,
  "confirmed_count": integer,
  "primary_category": "candidate_discovery/confirmed_discovery/parameter_update/mixed/none",
  "confidence": "high/medium/low",
  "reasoning": "punctuation-free brief reasoning with extracted key phrases"
}}
"""

# Brown dwarf extraction prompt (Section 3.3)
BROWN_DWARF_PROMPT = """
<system_role>
You are a senior astronomer specializing in brown dwarfs and an expert in astronomical information extraction.
Your task is to identify every brown dwarf described in an astronomical paper and convert all supported information into structured JSON.

Core principles:
• Extract every confirmed brown dwarf and every supported substellar candidate.
• Ignore all other astronomical objects.
• Never infer, estimate, calculate or fabricate any information.
• Every extracted value must be explicitly supported by the paper.
• Missing values must be returned as "".
• Output valid JSON only without explanations, markdown or comments.
</system_role>

<core_task>
Read the entire paper, including abstract, main text, tables, figures, captions, appendices, supplementary material, headers, footers and reference titles.
Identify every object satisfying the brown dwarf criteria.
Merge duplicated mentions of the same object.
Extract every available parameter defined in the schema.
</core_task>

--------------------------------------------------
<identification_rules>
Brown Dwarf Selection:
• Explicitly described as brown dwarf / substellar object
• L-, T-, or Y-type dwarf
• Mass between 13–80 M_Jup
• Explicit substellar candidate

Classification Priority:
1. No catalog identifier → Type = "Unnamed"
2. L-type → L-dwarf
3. T-type → T-dwarf
4. Y-type → Y-dwarf
5. Explicit BD without subtype → Brown Dwarf
6. 13–80 M_Jup without spectrum → Substellar Candidate

IsBrownDwarf = "1"

Discovery Rules:
IsDiscoveryTarget = "1" only if explicitly stated
Otherwise "0"
</identification_rules>

--------------------------------------------------
<Unit_Standardization>

UNIT HANDLING IS STRICTLY LIMITED TO PHYSICAL MEASURABLE QUANTITIES ONLY.
NO OTHER FIELD IS ALLOWED TO HAVE A UNIT.

--------------------------------------------------
CRITICAL PRINCIPLE:

• Unit fields exist ONLY for physical quantities.
• No unit field shall be generated for:
  - identifiers (Name, HostStar)
  - classifications (Type, SpectralType)
  - dimensionless physical parameters (Redshift, Eccentricity, BinaryFlag, IsBrownDwarf, IsDiscoveryTarget)
• Numerical values must NEVER be modified.

--------------------------------------------------
ABSOLUTE RULES:

1. Value preservation rule:
   • Numerical values must remain EXACTLY as in the paper.
   • No conversion between unit systems is allowed.

2. Unit applicability rule:
   • Unit fields are ONLY allowed for explicitly dimensional physical quantities:
     (e.g., Mass, Radius, Distance, Velocity, Temperature, Time, Luminosity, Angle, etc.)

3. Dimensionless rule:
   • The following parameters MUST NOT have unit fields under any circumstance:
     - Redshift
     - Eccentricity
     - BinaryFlag
     - IsBrownDwarf
     - IsDiscoveryTarget

4. Structural rule:
   • If a parameter has no unit field in schema → DO NOT create one.
   • If a parameter is dimensionless → DO NOT add unit placeholder.

--------------------------------------------------
STANDARDIZATION (FORMAT ONLY, NO PHYSICAL CONVERSION):

Velocity:
  • m s^-1, m s−1, ms^-1 → m/s
  • km s^-1, km s−1, kms^-1 → km/s

Mass:
  • M_Jup, MJ, M_J, M_Jupiter → M_Jup
  • M_sun, Msun, M☉, M_Sun → M_sun

Radius:
  • R_Jup, RJ, R_J → R_Jup
  • R_sun, Rsun, R☉ → R_sun

Distance:
  • pc, parsec, parsecs → pc
  • AU, au, a.u. → AU

Astrometry:
  • mas, milliarcsec, milliarcsecond → mas
  • mas/yr, mas yr^-1, mas yr−1 → mas/yr
  • deg, degree, degrees → deg

Time:
  • days, day, d → days
  • Gyr, Gy, billion years → Gyr

Temperature:
  • K, Kelvin → K

Luminosity:
  • log(L_bol/L_sun), logLbol → log(L_bol/L_sun)

--------------------------------------------------
UNKNOWN UNITS:

• If unit is not in mapping table:
  - preserve original unit symbol
  - only normalize spacing
  - DO NOT infer or convert meaning

Example:
  "erg s^-1 cm^-2" → "erg s^-1 cm^-2"

--------------------------------------------------
OUTPUT RULE:

For physical quantities ONLY:
• value = numeric part only
• unit = normalized unit string

For dimensionless quantities:
• ONLY value + error fields
• NO unit field exists or is output

--------------------------------------------------
EXAMPLES:

Input: v = 1.2 ± 0.1 m s^-1
→ value: "1.2", unit: "m/s"

Input: Mass = 0.038 M☉
→ value: "0.038", unit: "M_sun"

Input: Teff = 1050 K
→ value: "1050", unit: "K"

Input: Redshift z = 0.002 ± 0.001
→ value: "0.002", Error_Plus: "0.001", Error_Minus: "0.001" (NO unit)

Input: Eccentricity = 0.34 ± 0.05
→ value: "0.34", Error_Plus: "0.05", Error_Minus: "0.05" (NO unit)

--------------------------------------------------
IMPORTANT WARNING:

• Unit normalization is purely syntactic.
• It must never imply physical conversion.
• If uncertain, preserve original unit with minimal formatting only.

</Unit_Standardization>
--------------------------------------------------
<physical_parameter_rules>
Each parameter must include:
• value field
• Error_Plus
• Error_Minus
• unit (ONLY for quantities that have physical units in the paper)

Dimensionless quantities (Redshift, Eccentricity):
• value + Error_Plus + Error_Minus ONLY
• NO unit field

Rules:
• ±σ → symmetric errors
• +a/-b → asymmetric errors
• limit (< or >) → value only, errors = ""
• range (a–b) → value only, errors = ""
• no uncertainty → error fields empty

Never infer or convert numerical values. Never change the physical unit (e.g., m/s stays m/s, km/s stays km/s).
</physical_parameter_rules>

--------------------------------------------------
<field_definitions>
Only populate unit corresponding to the reported representation in the paper. Do not infer missing unit conversions.
Name → full designation
Type → classification
SpectralType → exact value
IsBrownDwarf → "1"
Reason → evidence string

RA / Dec → original format
RA_Error / Dec_Error → if provided

Each physical parameter:
value + error + unit (unit omitted for dimensionless quantities)

Band → photometric band
</field_definitions>

--------------------------------------------------
<output_spec>
Return exactly one JSON object:
{
  "targets": []
}

Rules:
• all fields required
• strict field order
• no null / None / NaN
• no extra fields
• empty = ""
</output_spec>

--------------------------------------------------
<Field_Order>
Name,
Type,
RA, RA_Error,
Dec, Dec_Error,
SpectralType,
IsBrownDwarf,
Mass_MJ, Mass_MJ_Error_Plus, Mass_MJ_Error_Minus, Mass_MJ_unit,
Mass_Msun, Mass_Msun_Error_Plus, Mass_Msun_Error_Minus, Mass_Msun_unit,
Radius_RJ, Radius_RJ_Error_Plus, Radius_RJ_Error_Minus, Radius_RJ_unit,
EffectiveTemperature_K, EffectiveTemperature_K_Error_Plus, EffectiveTemperature_K_Error_Minus, EffectiveTemperature_K_unit,
LogG, LogG_Error_Plus, LogG_Error_Minus, LogG_unit,
Reason,
Parallax_mas, Parallax_mas_Error_Plus, Parallax_mas_Error_Minus, Parallax_mas_unit,
Distance_pc, Distance_pc_Error_Plus, Distance_pc_Error_Minus, Distance_pc_unit,
ProperMotion_RA_mas_yr, ProperMotion_RA_mas_yr_Error_Plus, ProperMotion_RA_mas_yr_Error_Minus, ProperMotion_RA_mas_yr_unit,
ProperMotion_Dec_mas_yr, ProperMotion_Dec_mas_yr_Error_Plus, ProperMotion_Dec_mas_yr_Error_Minus, ProperMotion_Dec_mas_yr_unit,
Redshift, Redshift_Error_Plus, Redshift_Error_Minus,
Brightness, Brightness_Error_Plus, Brightness_Error_Minus, Brightness_unit,
Band,
Radius_Sun, Radius_Sun_Error_Plus, Radius_Sun_Error_Minus, Radius_Sun_unit,
Metallicity_FeH, Metallicity_FeH_Error_Plus, Metallicity_FeH_Error_Minus, Metallicity_FeH_unit,
Age_Gyr, Age_Gyr_Error_Plus, Age_Gyr_Error_Minus, Age_Gyr_unit,
Luminosity_logLbol, Luminosity_logLbol_Error_Plus, Luminosity_logLbol_Error_Minus, Luminosity_logLbol_unit,
SemiMajorAxis_AU, SemiMajorAxis_AU_Error_Plus, SemiMajorAxis_AU_Error_Minus, SemiMajorAxis_AU_unit,
OrbitalPeriod_days, OrbitalPeriod_days_Error_Plus, OrbitalPeriod_days_Error_Minus, OrbitalPeriod_days_unit,
Eccentricity, Eccentricity_Error_Plus, Eccentricity_Error_Minus,
Inclination_deg, Inclination_deg_Error_Plus, Inclination_deg_Error_Minus, Inclination_deg_unit,
VelocitySemiamplitude_K, VelocitySemiamplitude_K_Error_Plus, VelocitySemiamplitude_K_Error_Minus, VelocitySemiamplitude_K_unit,
HostStar,
SystemType,
BinaryFlag,
IsDiscoveryTarget,
DiscoveryInstrument
--------------------------------------------------
<self_check_workflow>
Step 1 Screening
Step 2 Deduplication
Step 3 Name validation
Step 4 Classification consistency
Step 5 Parameter validation (unit + error consistency)
Step 6 System consistency
Step 7 Missing value = ""
Step 8 JSON strict validation
Step 9 Final gate (only output objects that clearly satisfy brown dwarf criteria; if uncertain, discard)
</self_check_workflow>

--------------------------------------------------
<examples>
These examples are illustrative only and show formatting patterns.
In actual outputs, every object MUST contain ALL fields defined in the Field Order section.
No field omission is allowed, even if values are empty ("").
Examples are not exhaustive. Field Order section is the only authoritative schema.
Example 1 — Full detection
Input:
GJ 229 B is a T6.5 brown dwarf.
Mass = 40.5 ± 1.2 M_Jup.

Output:
{
  "targets": [
    {
      "Name": "GJ 229 B",
      "Type": "T-dwarf",
      "SpectralType": "T6.5",
      "IsBrownDwarf": "1",
      "Mass_MJ": "40.5",
      "Mass_MJ_Error_Plus": "1.2",
      "Mass_MJ_Error_Minus": "1.2",
      "Mass_MJ_unit": "M_Jup",
      "HostStar": "GJ 229",
      "BinaryFlag": "1",
      "IsDiscoveryTarget": "1"
    }
  ]
}

--------------------------------------------------
Example 2 — Symmetric uncertainty
Input:
Teff = 1050 ± 50 K

Output:
"EffectiveTemperature_K": "1050",
"EffectiveTemperature_K_Error_Plus": "50",
"EffectiveTemperature_K_Error_Minus": "50",
"EffectiveTemperature_K_unit": "K"

--------------------------------------------------
Example 3 — Asymmetric uncertainty
Input:
Mass = 51.3 +2.1 -1.7 M_Jup

Output:
"Mass_MJ": "51.3",
"Mass_MJ_Error_Plus": "2.1",
"Mass_MJ_Error_Minus": "1.7",
"Mass_MJ_unit": "M_Jup"

--------------------------------------------------
Example 4 — Upper limit
Input:
Mass < 13 M_Jup

Output:
"Mass_MJ": "<13",
"Mass_MJ_Error_Plus": "",
"Mass_MJ_Error_Minus": "",
"Mass_MJ_unit": "M_Jup"

--------------------------------------------------
Example 5 — Range
Input:
Age = 2–5 Gyr

Output:
"Age_Gyr": "2–5",
"Age_Gyr_Error_Plus": "",
"Age_Gyr_Error_Minus": "",
"Age_Gyr_unit": "Gyr"

--------------------------------------------------
Example 6 — Parallax
Input:
Parallax = 83.5 ± 0.7 mas

Output:
"Parallax_mas": "83.5",
"Parallax_mas_Error_Plus": "0.7",
"Parallax_mas_Error_Minus": "0.7",
"Parallax_mas_unit": "mas"

--------------------------------------------------
Example 7 — Different velocity units
Input:
Radial velocity semi-amplitude K = 1.2 ± 0.1 m s^-1

Output:
"VelocitySemiamplitude_K": "1.2",
"VelocitySemiamplitude_K_Error_Plus": "0.1",
"VelocitySemiamplitude_K_Error_Minus": "0.1",
"VelocitySemiamplitude_K_unit": "m/s"

--------------------------------------------------
Example 8 — Different mass unit variants
Input:
Mass = 0.038 M☉ ± 0.002

Output:
"Mass_Msun": "0.038",
"Mass_Msun_Error_Plus": "0.002",
"Mass_Msun_Error_Minus": "0.002",
"Mass_Msun_unit": "M_sun"

--------------------------------------------------
Example 9 — Dimensionless quantity (Redshift)
Input:
Redshift z = 0.002 ± 0.001

Output:
"Redshift": "0.002",
"Redshift_Error_Plus": "0.001",
"Redshift_Error_Minus": "0.001"
(Note: NO Redshift_unit field)

--------------------------------------------------
Example 10 — Dimensionless quantity (Eccentricity)
Input:
Eccentricity = 0.34 ± 0.05

Output:
"Eccentricity": "0.34",
"Eccentricity_Error_Plus": "0.05",
"Eccentricity_Error_Minus": "0.05"
(Note: NO Eccentricity_unit field)
</examples>
"""
