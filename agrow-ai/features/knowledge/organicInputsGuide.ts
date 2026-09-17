/** Farmer-facing text from the owner's guide; English preserved verbatim.
 * Tamil is a translation, not a new treatment recommendation.
 * Internal business notes and commerce features are intentionally excluded.
 */
export interface OrganicRecipeText { title: string; summary: string; body: string }
export interface OrganicRecipe { id: string; category: string; en: OrganicRecipeText; ta: OrganicRecipeText }
export const ORGANIC_INPUTS_GUIDE: readonly OrganicRecipe[] = [
  {
    "id": "vermicompost",
    "category": "nutrition",
    "en": {
      "title": "Vermicompost",
      "summary": "Compost made by earthworms breaking down cow dung and crop waste into nutrient-rich humus.",
      "body": "Materials needed\nCow dung\nDry crop waste / dried leaves\nEarthworms (Eisenia fetida species)\nShaded pit or bin\nWater for moisture\nProcedure\nLayer cow dung and chopped dry waste in a shaded pit or bin.\nAdd earthworms once the heap has cooled (not fresh/hot dung).\nKeep moist (not waterlogged) and covered with a jute sack or dry leaves.\nTurn gently every 15 days to aerate.\nHarvest when material turns dark, crumbly, and soil-like.\nTime to ready\n45–60 days\nBenefits\nRich in NPK and micronutrients\nImproves soil structure and water retention\nBoosts beneficial soil microbes\nHow to use\nApply 2–3 tons/acre broadcast before sowing, or as topdressing during crop growth."
    },
    "ta": {
      "title": "மண்புழு உரம்",
      "summary": "மாட்டுச் சாணத்தையும் பயிர்க் கழிவுகளையும் மண்புழுக்கள் சிதைத்து, ஊட்டச்சத்து நிறைந்த மட்குப்பொருளாக மாற்றும் உரம்.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சாணம்\nஉலர்ந்த பயிர்க் கழிவுகள் / உலர்ந்த இலைகள்\nமண்புழுக்கள் (Eisenia fetida இனம்)\nநிழலான குழி அல்லது தொட்டி\nஈரப்பதத்திற்கான நீர்\nசெய்முறை\nநிழலான குழி அல்லது தொட்டியில் மாட்டுச் சாணத்தையும் நறுக்கிய உலர் கழிவுகளையும் அடுக்கவும்.\nகுவியல் குளிர்ந்த பிறகு மண்புழுக்களைச் சேர்க்கவும் (புதிய அல்லது சூடான சாணத்தில் அல்ல).\nநீர் தேங்காமல் ஈரமாக வைத்திருந்து, சணல் சாக்கு அல்லது உலர்ந்த இலைகளால் மூடவும்.\nகாற்றோட்டத்திற்காக 15 நாட்களுக்கு ஒருமுறை மெதுவாகக் கிளறவும்.\nபொருள் கருமையாகவும் உதிரியாகவும் மண் போன்றும் மாறியதும் சேகரிக்கவும்.\nதயாராகும் காலம்\n45–60 நாட்கள்\nநன்மைகள்\nநைட்ரஜன், பாஸ்பரஸ், பொட்டாசியம் மற்றும் நுண்ணூட்டச்சத்துகள் நிறைந்தது\nமண் அமைப்பையும் நீர்ப் பிடிப்பையும் மேம்படுத்துகிறது\nநன்மை செய்யும் மண் நுண்ணுயிர்களை அதிகரிக்கிறது\nபயன்படுத்தும் முறை\nவிதைப்பதற்கு முன் ஏக்கருக்கு 2–3 டன் பரப்பவும் அல்லது பயிர் வளரும்போது மேலுரமாக இடவும்."
    }
  },
  {
    "id": "fym",
    "category": "nutrition",
    "en": {
      "title": "Farmyard Manure (FYM) Composting",
      "summary": "Traditional heap composting of cow dung, urine-soaked bedding, and crop residue.",
      "body": "Materials needed\nCow dung\nUrine-soaked cattle shed bedding/straw\nCrop residue\nProcedure\nHeap materials in a shaded area, layering dung and residue.\nKeep the heap moist through dry spells.\nTurn every 3–4 weeks to aerate and speed decomposition.\nLet mature fully before use.\nTime to ready\n3–4 months\nBenefits\nAdds bulk organic matter to soil\nSlow-release nutrients over the season\nImproves long-term soil fertility\nHow to use\nApply 5–10 tons/acre during land preparation, before sowing."
    },
    "ta": {
      "title": "தொழுஉரம் (FYM) மக்கவைத்தல்",
      "summary": "மாட்டுச் சாணம், சிறுநீரால் நனைந்த படுக்கைப் பொருள் மற்றும் பயிர்க் கழிவுகளை குவியலாக மக்கவைக்கும் பாரம்பரிய முறை.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சாணம்\nசிறுநீரால் நனைந்த மாட்டுக் கொட்டகைப் படுக்கைப் பொருள் / வைக்கோல்\nபயிர்க் கழிவுகள்\nசெய்முறை\nநிழலான இடத்தில் சாணத்தையும் கழிவுகளையும் அடுக்கிக் குவிக்கவும்.\nவறண்ட காலங்களிலும் குவியலை ஈரமாக வைத்திருக்கவும்.\nகாற்றோட்டத்திற்கும் விரைவாக மக்குவதற்கும் 3–4 வாரங்களுக்கு ஒருமுறை திருப்பவும்.\nபயன்படுத்துவதற்கு முன் முழுமையாக மக்க விடவும்.\nதயாராகும் காலம்\n3–4 மாதங்கள்\nநன்மைகள்\nமண்ணில் அதிக அளவு கரிமப் பொருளைச் சேர்க்கிறது\nபருவம் முழுவதும் மெதுவாக ஊட்டச்சத்துகளை விடுவிக்கிறது\nநீண்டகால மண் வளத்தை மேம்படுத்துகிறது\nபயன்படுத்தும் முறை\nவிதைப்பதற்கு முன் நிலம் தயாரிக்கும்போது ஏக்கருக்கு 5–10 டன் இடவும்."
    }
  },
  {
    "id": "nadep",
    "category": "nutrition",
    "en": {
      "title": "NADEP Compost",
      "summary": "A space-efficient composting method using a brick/cement tank with layered waste and soil.",
      "body": "Materials needed\nBrick or cement tank (standard NADEP size)\nCrop waste\nCow dung slurry (dung mixed with water)\nFine soil for dusting between layers\nProcedure\nLayer crop waste, then a thin layer of dung slurry, then a dusting of soil.\nRepeat layers until the tank is full.\nSeal the top with a mud plaster.\nKeep moist by watering periodically through small holes.\nEmpty and use once fully decomposed.\nTime to ready\n90–120 days\nBenefits\nMore efficient use of space than open heaps\nGood microbial activity and even decomposition\nReduces nutrient loss compared to open composting\nHow to use\nApply 4–5 tons/acre before sowing."
    },
    "ta": {
      "title": "NADEP கம்போஸ்ட்",
      "summary": "செங்கல் அல்லது சிமெண்ட் தொட்டியில் கழிவுகளையும் மண்ணையும் அடுக்கி, இடத்தைச் சிக்கனமாகப் பயன்படுத்தும் மக்கவைக்கும் முறை.",
      "body": "தேவையான பொருட்கள்\nசெங்கல் அல்லது சிமெண்ட் தொட்டி (வழக்கமான NADEP அளவு)\nபயிர்க் கழிவுகள்\nமாட்டுச் சாணக் கரைசல் (நீருடன் கலந்த சாணம்)\nஅடுக்குகளுக்கு இடையில் தூவுவதற்கான நுண்ணிய மண்\nசெய்முறை\nபயிர்க் கழிவுகள், மெல்லிய சாணக் கரைசல் அடுக்கு, பின்னர் மண் தூவல் என அடுக்கவும்.\nதொட்டி நிரம்பும் வரை அடுக்குகளைத் தொடரவும்.\nமேற்பகுதியை சேற்றுப் பூச்சால் மூடவும்.\nசிறு துளைகள் வழியாக அவ்வப்போது நீர் ஊற்றி ஈரமாக வைத்திருக்கவும்.\nமுழுமையாக மக்கியதும் காலி செய்து பயன்படுத்தவும்.\nதயாராகும் காலம்\n90–120 நாட்கள்\nநன்மைகள்\nதிறந்த குவியல்களைவிட இடத்தைச் சிக்கனமாகப் பயன்படுத்துகிறது\nநல்ல நுண்ணுயிர் செயல்பாடும் சீரான மக்குதலும்\nதிறந்த மக்கவைத்தலைவிட ஊட்டச்சத்து இழப்பைக் குறைக்கிறது\nபயன்படுத்தும் முறை\nவிதைப்பதற்கு முன் ஏக்கருக்கு 4–5 டன் இடவும்."
    }
  },
  {
    "id": "jeevamrutham",
    "category": "nutrition",
    "en": {
      "title": "Jeevamrutham",
      "summary": "A fast-fermenting liquid fertilizer that boosts soil microbial activity.",
      "body": "Materials needed\nCow dung\nCow urine\nJaggery\nPulse flour (besan)\nWater\nA handful of undisturbed soil (for native microbes)\nProcedure\nMix all ingredients in a barrel of water.\nStir daily, twice a day if possible.\nFerment in the shade for 48–72 hours before use.\nTime to ready\n2–3 days\nBenefits\nRapidly boosts soil microbial life\nMakes existing soil nutrients more available to roots\nVery low cost to produce\nHow to use\nDilute with water; apply as a soil drench or light spray every 15 days."
    },
    "ta": {
      "title": "ஜீவாமிர்தம்",
      "summary": "மண் நுண்ணுயிர் செயல்பாட்டை அதிகரிக்கும், விரைவாக நொதிக்கும் திரவ உரம்.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சாணம்\nமாட்டுச் சிறுநீர்\nவெல்லம்\nபயறு மாவு (கடலை மாவு)\nநீர்\nகிளறப்படாத மண் ஒரு கைப்பிடி (உள்ளூர் நுண்ணுயிர்களுக்காக)\nசெய்முறை\nநீர் நிரம்பிய பீப்பாயில் அனைத்துப் பொருட்களையும் கலக்கவும்.\nதினமும் கிளறவும்; முடிந்தால் நாளுக்கு இருமுறை.\nபயன்படுத்துவதற்கு முன் நிழலில் 48–72 மணி நேரம் நொதிக்க விடவும்.\nதயாராகும் காலம்\n2–3 நாட்கள்\nநன்மைகள்\nமண் நுண்ணுயிர்களை விரைவாக அதிகரிக்கிறது\nமண்ணில் உள்ள ஊட்டச்சத்துகள் வேர்களுக்கு எளிதில் கிடைக்க உதவுகிறது\nதயாரிப்புச் செலவு மிகக் குறைவு\nபயன்படுத்தும் முறை\nநீருடன் நீர்த்துப்போகச் செய்து, 15 நாட்களுக்கு ஒருமுறை மண்ணில் ஊற்றவும் அல்லது லேசாகத் தெளிக்கவும்."
    }
  },
  {
    "id": "panchagavya",
    "category": "nutrition",
    "en": {
      "title": "Panchagavya",
      "summary": "A fermented growth booster made from five cow products, used as both fertilizer and mild pest deterrent.",
      "body": "Materials needed\nCow dung\nCow urine\nMilk\nCurd\nGhee\nBanana\nJaggery\nTender coconut water\nProcedure\nMix cow dung and ghee first, let sit 3 days.\nAdd remaining ingredients in the traditional sequence.\nFerment for 15–20 days, stirring daily.\nFilter before use or bottling.\nTime to ready\n≈15–20 days\nBenefits\nPromotes flowering and fruiting\nImproves plant immunity and stress tolerance\nMild pest and disease resistance\nHow to use\nDilute (roughly 3%) and apply as a foliar spray every 15 days."
    },
    "ta": {
      "title": "பஞ்சகவ்யா",
      "summary": "ஐந்து மாட்டுப் பொருட்களால் தயாரிக்கப்படும் நொதித்த வளர்ச்சி ஊக்கி; உரமாகவும் லேசான பூச்சி விரட்டியாகவும் பயன்படுகிறது.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சாணம்\nமாட்டுச் சிறுநீர்\nபால்\nதயிர்\nநெய்\nவாழைப்பழம்\nவெல்லம்\nஇளநீர்\nசெய்முறை\nமுதலில் மாட்டுச் சாணத்தையும் நெய்யையும் கலந்து 3 நாட்கள் வைத்திருக்கவும்.\nமீதிப் பொருட்களை பாரம்பரிய வரிசையில் சேர்க்கவும்.\nதினமும் கிளறி 15–20 நாட்கள் நொதிக்க விடவும்.\nபயன்படுத்தும் முன் அல்லது பாட்டிலில் நிரப்பும் முன் வடிகட்டவும்.\nதயாராகும் காலம்\nசுமார் 15–20 நாட்கள்\nநன்மைகள்\nபூத்தலையும் காய்ப்பையும் ஊக்குவிக்கிறது\nதாவர நோய் எதிர்ப்பையும் அழுத்தத்தைத் தாங்கும் திறனையும் மேம்படுத்துகிறது\nலேசான பூச்சி மற்றும் நோய் எதிர்ப்பு\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து (சுமார் 3%), 15 நாட்களுக்கு ஒருமுறை இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "green-manuring",
    "category": "nutrition",
    "en": {
      "title": "Green Manuring",
      "summary": "Growing a fast-growing legume crop and ploughing it into the soil before the main crop, to fix nitrogen naturally.",
      "body": "Materials needed\nDhaincha or Sunhemp seeds\nProcedure\nBroadcast-sow the seeds ahead of the main crop season.\nLet the crop grow for about 45 days.\nPlough the green crop into the soil before it flowers.\nTime to ready\n45–50 days growth, then incorporation\nBenefits\nFixes atmospheric nitrogen into the soil\nAdds organic matter\nSuppresses weeds during the growing window\nHow to use\nDone in-situ, in the field, before the main crop is sown."
    },
    "ta": {
      "title": "பசுந்தாள் உரமிடுதல்",
      "summary": "முக்கியப் பயிருக்கு முன் வேகமாக வளரும் பயறு வகைப் பயிரை வளர்த்து மண்ணில் உழுது சேர்த்து, இயற்கையாக நைட்ரஜனை நிலைநிறுத்தும் முறை.",
      "body": "தேவையான பொருட்கள்\nதக்கைப்பூண்டு அல்லது சணப்பை விதைகள்\nசெய்முறை\nமுக்கியப் பயிர்ப் பருவத்திற்கு முன் விதைகளைப் பரவலாகத் தூவி விதைக்கவும்.\nசுமார் 45 நாட்கள் வளர விடவும்.\nபூக்கும் முன் பசுமையான பயிரை மண்ணில் உழுது சேர்க்கவும்.\nதயாராகும் காலம்\n45–50 நாட்கள் வளர்ச்சி, பின்னர் மண்ணில் சேர்த்தல்\nநன்மைகள்\nவளிமண்டல நைட்ரஜனை மண்ணில் நிலைநிறுத்துகிறது\nகரிமப் பொருளைச் சேர்க்கிறது\nவளரும் காலத்தில் களைகளை அடக்குகிறது\nபயன்படுத்தும் முறை\nமுக்கியப் பயிரை விதைப்பதற்கு முன் அதே வயலில் செய்யப்படுகிறது."
    }
  },
  {
    "id": "vermiwash",
    "category": "nutrition",
    "en": {
      "title": "Vermiwash",
      "summary": "The liquid that drains from a vermicompost bed, rich in nutrients and worm secretions.",
      "body": "Materials needed\nAn active vermicompost bed with a drainage outlet\nWater\nProcedure\nSlowly pass water through the top of a mature vermicompost bed.\nCollect the liquid that drains out from the bottom outlet.\nTime to ready\nA few hours per batch, ongoing while the bed is active\nBenefits\nFast-acting liquid nutrient source\nMild pest-deterrent properties\nA useful by-product of vermicomposting at no extra material cost\nHow to use\nDilute and apply as a foliar spray."
    },
    "ta": {
      "title": "மண்புழு திரவம் (Vermiwash)",
      "summary": "மண்புழு உரப் படுக்கையிலிருந்து வடிந்து வரும், ஊட்டச்சத்துகளும் மண்புழு சுரப்புகளும் நிறைந்த திரவம்.",
      "body": "தேவையான பொருட்கள்\nவடிகால் வெளியேற்றம் உள்ள செயல்படும் மண்புழு உரப் படுக்கை\nநீர்\nசெய்முறை\nமுதிர்ந்த மண்புழு உரப் படுக்கையின் மேல் மெதுவாக நீர் செலுத்தவும்.\nகீழ் வெளியேற்றத்திலிருந்து வடியும் திரவத்தைச் சேகரிக்கவும்.\nதயாராகும் காலம்\nஒரு தொகுதிக்கு சில மணி நேரம்; படுக்கை செயல்படும் வரை தொடர்ந்து பெறலாம்\nநன்மைகள்\nவிரைவாகச் செயல்படும் திரவ ஊட்டச்சத்து ஆதாரம்\nலேசான பூச்சி விரட்டும் பண்புகள்\nகூடுதல் பொருட்செலவின்றி மண்புழு உரத்திலிருந்து கிடைக்கும் பயனுள்ள துணைப் பொருள்\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "bone-meal-faa",
    "category": "nutrition",
    "en": {
      "title": "Bone Meal / Fish Amino Acid",
      "summary": "Bone meal is ground, dried bone for phosphorus and calcium; Fish Amino Acid (FAA) is a fermented liquid extract from fish waste.",
      "body": "Materials needed\nWaste fish or bones\nJaggery (for FAA)\nProcedure\nFor FAA: layer fish waste with jaggery in a sealed container; ferment 30–45 days in shade, then strain.\nFor bone meal: dry bones fully in the sun, then grind to a fine powder.\nTime to ready\n30–45 days (FAA); several days of drying plus grinding (bone meal)\nBenefits\nHigh in phosphorus and calcium (bone meal)\nRich in potassium and natural growth compounds (FAA)\nHow to use\nFAA: dilute and spray. Bone meal: mix directly into soil."
    },
    "ta": {
      "title": "எலும்புத்தூள் / மீன் அமினோ அமிலம்",
      "summary": "எலும்புத்தூள் என்பது பாஸ்பரஸ் மற்றும் கால்சியத்திற்கான உலர்த்தி அரைத்த எலும்பு; மீன் அமினோ அமிலம் (FAA) என்பது மீன் கழிவிலிருந்து பெறப்படும் நொதித்த திரவச் சாறு.",
      "body": "தேவையான பொருட்கள்\nமீன் கழிவு அல்லது எலும்புகள்\nவெல்லம் (FAA-க்கு)\nசெய்முறை\nFAA: மூடிய பாத்திரத்தில் மீன் கழிவையும் வெல்லத்தையும் அடுக்கி, நிழலில் 30–45 நாட்கள் நொதிக்கவிட்டு வடிகட்டவும்.\nஎலும்புத்தூள்: எலும்புகளை வெயிலில் முழுமையாக உலர்த்தி, நுண்ணிய தூளாக அரைக்கவும்.\nதயாராகும் காலம்\n30–45 நாட்கள் (FAA); சில நாட்கள் உலர்த்துதல் மற்றும் அரைத்தல் (எலும்புத்தூள்)\nநன்மைகள்\nபாஸ்பரஸ் மற்றும் கால்சியம் அதிகம் (எலும்புத்தூள்)\nபொட்டாசியமும் இயற்கை வளர்ச்சிக் கூட்டுப்பொருட்களும் நிறைந்தது (FAA)\nபயன்படுத்தும் முறை\nFAA: நீர்த்துப்போகச் செய்து தெளிக்கவும். எலும்புத்தூள்: நேரடியாக மண்ணில் கலக்கவும்."
    }
  },
  {
    "id": "compost-tea",
    "category": "nutrition",
    "en": {
      "title": "Compost Tea",
      "summary": "A quick liquid microbial inoculant made by steeping finished compost in water.",
      "body": "Materials needed\nFinished compost\nWater\nMolasses (optional, feeds microbes)\nProcedure\nSteep compost in water for 24–48 hours.\nAerate occasionally if possible (stir or bubble).\nStrain out solids before use.\nTime to ready\n1–2 days\nBenefits\nQuick microbial boost to soil or leaves\nImproves plant immunity\nUses compost already on hand\nHow to use\nApply as a soil drench or foliar spray."
    },
    "ta": {
      "title": "கம்போஸ்ட் தேநீர்",
      "summary": "முழுமையாக மக்கிய உரத்தை நீரில் ஊறவைத்து தயாரிக்கும் விரைவான திரவ நுண்ணுயிர் ஊக்கி.",
      "body": "தேவையான பொருட்கள்\nமுழுமையாக மக்கிய கம்போஸ்ட்\nநீர்\nமொலாசஸ் (விருப்பத்திற்கேற்ப; நுண்ணுயிர்களுக்கு உணவு)\nசெய்முறை\nகம்போஸ்ட்டை நீரில் 24–48 மணி நேரம் ஊறவைக்கவும்.\nமுடிந்தால் அவ்வப்போது கிளறி அல்லது காற்றுக் குமிழ்களைச் செலுத்தி காற்றோட்டம் அளிக்கவும்.\nபயன்படுத்தும் முன் திடப்பொருட்களை வடிகட்டவும்.\nதயாராகும் காலம்\n1–2 நாட்கள்\nநன்மைகள்\nமண் அல்லது இலைகளில் நுண்ணுயிர்களை விரைவாக அதிகரிக்கிறது\nதாவர நோய் எதிர்ப்பை மேம்படுத்துகிறது\nஏற்கெனவே உள்ள கம்போஸ்ட்டைப் பயன்படுத்துகிறது\nபயன்படுத்தும் முறை\nமண்ணில் ஊற்றவும் அல்லது இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "neem-nske",
    "category": "protection",
    "en": {
      "title": "Neem Oil / Neem Seed Kernel Extract (NSKE)",
      "summary": "A broad-spectrum organic pesticide made from neem seeds.",
      "body": "Materials needed\nNeem seeds/kernels\nWater\nA small amount of soap or detergent (emulsifier)\nProcedure\nCrush neem seeds/kernels into a coarse powder.\nSoak overnight in water.\nFilter the liquid the next day.\nAdd a little soap as an emulsifier before spraying.\nTime to ready\nAbout 1 day\nBenefits\nBroad-spectrum pest repellent\nSafe for beneficial insects at correct dosage\nLow cost, locally sourced\nHow to use\nDilute and spray every 7–10 days."
    },
    "ta": {
      "title": "வேப்பெண்ணெய் / வேப்பங்கொட்டைச் சாறு (NSKE)",
      "summary": "வேப்ப விதைகளிலிருந்து தயாரிக்கப்படும், பலவகைப் பூச்சிகளுக்கு எதிரான இயற்கை பூச்சிக்கொல்லி.",
      "body": "தேவையான பொருட்கள்\nவேப்ப விதைகள் / கொட்டைப் பருப்புகள்\nநீர்\nசிறிதளவு சோப்பு அல்லது சலவைப்பொருள் (கலப்பதற்கான ஊடகம்)\nசெய்முறை\nவேப்ப விதைகள் / கொட்டைப் பருப்புகளை கொரகொரப்பான தூளாக நசுக்கவும்.\nநீரில் இரவு முழுவதும் ஊறவைக்கவும்.\nமறுநாள் திரவத்தை வடிகட்டவும்.\nதெளிக்கும் முன் கலப்பதற்கு உதவ சிறிது சோப்பு சேர்க்கவும்.\nதயாராகும் காலம்\nசுமார் 1 நாள்\nநன்மைகள்\nபலவகைப் பூச்சிகளை விரட்டுகிறது\nசரியான அளவில் பயன்படுத்தும்போது நன்மை செய்யும் பூச்சிகளுக்கு பாதுகாப்பானது\nகுறைந்த செலவு; உள்ளூரில் கிடைக்கும் பொருட்கள்\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து 7–10 நாட்களுக்கு ஒருமுறை தெளிக்கவும்."
    }
  },
  {
    "id": "panchagavya-pest",
    "category": "protection",
    "en": {
      "title": "Panchagavya Pest Spray",
      "summary": "The same Panchagavya preparation used as a mild pest and disease deterrent (dual-use with the fertilizer form above).",
      "body": "Materials needed\nSee Panchagavya recipe above\nProcedure\nPrepare as described above.\nUse at slightly higher dilution when the goal is pest control rather than growth boosting.\nTime to ready\n≈15–20 days to prepare\nBenefits\nMild pest and fungal resistance\nDual-purpose with the fertilizer use case\nHow to use\nDilute and apply as a foliar spray during pest-pressure periods."
    },
    "ta": {
      "title": "பஞ்சகவ்யா பூச்சி விரட்டித் தெளிப்பு",
      "summary": "மேலே உள்ள அதே பஞ்சகவ்யா தயாரிப்பு, லேசான பூச்சி மற்றும் நோய் தடுப்பாகப் பயன்படுகிறது (உரப் பயன்பாட்டுடன் இரட்டைப் பயன்பாடு).",
      "body": "தேவையான பொருட்கள்\nமேலே உள்ள பஞ்சகவ்யா செய்முறையைப் பார்க்கவும்\nசெய்முறை\nமேலே விவரிக்கப்பட்டபடி தயாரிக்கவும்.\nவளர்ச்சி ஊக்குவிப்பைவிட பூச்சிக் கட்டுப்பாடு நோக்கமாக இருக்கும்போது சற்றுக் கூடுதலாக நீர்த்துப்போகச் செய்து பயன்படுத்தவும்.\nதயாராகும் காலம்\nதயாரிக்க சுமார் 15–20 நாட்கள்\nநன்மைகள்\nலேசான பூச்சி மற்றும் பூஞ்சை எதிர்ப்பு\nஉரப் பயன்பாட்டுடன் இரட்டைப் பயன்பாடு\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து பூச்சி அழுத்தம் உள்ள காலங்களில் இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "buttermilk",
    "category": "protection",
    "en": {
      "title": "Buttermilk Spray",
      "summary": "A simple, cheap fermented spray effective against fungal diseases like powdery mildew.",
      "body": "Materials needed\nSour buttermilk\nWater\nProcedure\nDilute buttermilk in water.\nLet the mixture sit and ferment for 3–4 days.\nStrain before spraying.\nTime to ready\n3–4 days\nBenefits\nControls fungal diseases (e.g. powdery mildew)\nVery cheap, uses kitchen by-product\nHow to use\nApply as a foliar spray."
    },
    "ta": {
      "title": "மோர் தெளிப்பு",
      "summary": "சாம்பல் நோய் போன்ற பூஞ்சை நோய்களுக்கு எதிராகப் பயன்படும் எளிய, மலிவான நொதித்த தெளிப்பு.",
      "body": "தேவையான பொருட்கள்\nபுளித்த மோர்\nநீர்\nசெய்முறை\nமோரை நீரில் நீர்த்துப்போகச் செய்யவும்.\nகலவையை 3–4 நாட்கள் வைத்து நொதிக்க விடவும்.\nதெளிக்கும் முன் வடிகட்டவும்.\nதயாராகும் காலம்\n3–4 நாட்கள்\nநன்மைகள்\nபூஞ்சை நோய்களைக் கட்டுப்படுத்துகிறது (எ.கா. சாம்பல் நோய்)\nமிகக் குறைந்த செலவு; சமையலறைத் துணைப் பொருளைப் பயன்படுத்துகிறது\nபயன்படுத்தும் முறை\nஇலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "garlic-chili",
    "category": "protection",
    "en": {
      "title": "Garlic-Chili Extract Spray",
      "summary": "A pungent natural spray that repels sucking pests and mites.",
      "body": "Materials needed\nGarlic\nGreen chili\nWater\nSoap (as a sticking agent)\nProcedure\nGrind garlic and chili together.\nSoak in water for 24 hours.\nStrain and add a little soap before spraying.\nTime to ready\n1 day\nBenefits\nRepels sucking pests and mites\nCheap and easy to prepare at home\nHow to use\nApply as a foliar spray every 7 days."
    },
    "ta": {
      "title": "பூண்டு–மிளகாய் சாறு தெளிப்பு",
      "summary": "சாறு உறிஞ்சும் பூச்சிகளையும் சிலந்திப்பூச்சிகளையும் விரட்டும் காரமான இயற்கைத் தெளிப்பு.",
      "body": "தேவையான பொருட்கள்\nபூண்டு\nபச்சை மிளகாய்\nநீர்\nசோப்பு (ஒட்டும் பொருளாக)\nசெய்முறை\nபூண்டையும் மிளகாயையும் ஒன்றாக அரைக்கவும்.\nநீரில் 24 மணி நேரம் ஊறவைக்கவும்.\nவடிகட்டி, தெளிக்கும் முன் சிறிது சோப்பு சேர்க்கவும்.\nதயாராகும் காலம்\n1 நாள்\nநன்மைகள்\nசாறு உறிஞ்சும் பூச்சிகளையும் சிலந்திப்பூச்சிகளையும் விரட்டுகிறது\nகுறைந்த செலவில் வீட்டிலேயே எளிதாகத் தயாரிக்கலாம்\nபயன்படுத்தும் முறை\n7 நாட்களுக்கு ஒருமுறை இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "cow-urine",
    "category": "protection",
    "en": {
      "title": "Cow Urine-Based Pest Repellents (Agniastra, Brahmastra)",
      "summary": "Traditional ZBNF (Zero Budget Natural Farming) pest-repellent decoctions based on cow urine and strong-smelling leaves.",
      "body": "Materials needed\nCow urine\nNeem leaves\nTobacco leaves, garlic, and green chili (for Agniastra) OR neem, custard apple, papaya, and guava leaves (for Brahmastra)\nProcedure\nBoil or ferment the mixture according to the specific formula.\nLet it settle and strain before use.\nTime to ready\nA few days (boiling plus settling time)\nBenefits\nBroad pest control\nVery low cost\nUses materials already available on most farms\nHow to use\nDilute and apply as a foliar spray."
    },
    "ta": {
      "title": "மாட்டுச் சிறுநீர் பூச்சி விரட்டிகள் (அக்னியாஸ்திரம், பிரம்மாஸ்திரம்)",
      "summary": "மாட்டுச் சிறுநீரும் கடுமையான மணமுள்ள இலைகளும் கொண்டு தயாரிக்கும் பாரம்பரிய ZBNF (செலவில்லா இயற்கை வேளாண்மை) பூச்சி விரட்டிக் கசாயங்கள்.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சிறுநீர்\nவேப்ப இலைகள்\nஅக்னியாஸ்திரத்திற்கு புகையிலை இலைகள், பூண்டு, பச்சை மிளகாய் அல்லது பிரம்மாஸ்திரத்திற்கு வேப்பம், சீத்தாப்பழம், பப்பாளி, கொய்யா இலைகள்\nசெய்முறை\nகுறிப்பிட்ட செய்முறைக்கு ஏற்ப கலவையைக் கொதிக்கவைக்கவும் அல்லது நொதிக்க விடவும்.\nதெளியவிட்டு, பயன்படுத்தும் முன் வடிகட்டவும்.\nதயாராகும் காலம்\nசில நாட்கள் (கொதிக்கவைத்தல் மற்றும் தெளியவிடுதல் உட்பட)\nநன்மைகள்\nபலவகைப் பூச்சிக் கட்டுப்பாடு\nமிகக் குறைந்த செலவு\nபெரும்பாலான பண்ணைகளில் ஏற்கெனவே கிடைக்கும் பொருட்களைப் பயன்படுத்துகிறது\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "trichoderma-compost",
    "category": "protection",
    "en": {
      "title": "Trichoderma-Enriched Compost",
      "summary": "Compost inoculated with Trichoderma, a beneficial fungus that suppresses soil-borne plant diseases.",
      "body": "Materials needed\nFinished compost or FYM\nTrichoderma viride culture (sourced from an agriculture department or KVK — not itself farmer-made from scratch)\nProcedure\nMix the Trichoderma culture into moist compost.\nIncubate in the shade for 7–10 days, keeping it moist.\nTime to ready\n7–10 days\nBenefits\nBiological control of soil-borne fungal disease\nImproves root health\nReduces dependence on chemical fungicides\nHow to use\nApply to soil at sowing or transplanting."
    },
    "ta": {
      "title": "டிரைக்கோடெர்மா செறிவூட்டிய கம்போஸ்ட்",
      "summary": "மண் மூலம் பரவும் தாவர நோய்களை அடக்கும் நன்மை செய்யும் பூஞ்சையான டிரைக்கோடெர்மா சேர்க்கப்பட்ட கம்போஸ்ட்.",
      "body": "தேவையான பொருட்கள்\nமுழுமையாக மக்கிய கம்போஸ்ட் அல்லது தொழுஉரம்\nTrichoderma viride வளர்ப்பு (வேளாண் துறை அல்லது KVK-இலிருந்து பெற வேண்டும்; விவசாயி தொடக்கத்திலிருந்து தானே தயாரிப்பதல்ல)\nசெய்முறை\nஈரமான கம்போஸ்ட்டில் டிரைக்கோடெர்மா வளர்ப்பைக் கலக்கவும்.\nஈரமாக வைத்திருந்து நிழலில் 7–10 நாட்கள் வளர விடவும்.\nதயாராகும் காலம்\n7–10 நாட்கள்\nநன்மைகள்\nமண் மூலம் பரவும் பூஞ்சை நோய்களுக்கு உயிரியல் கட்டுப்பாடு\nவேர் நலத்தை மேம்படுத்துகிறது\nவேதியியல் பூஞ்சைக்கொல்லிகளைச் சார்ந்திருப்பதைக் குறைக்கிறது\nபயன்படுத்தும் முறை\nவிதைக்கும் அல்லது நடவு செய்யும் நேரத்தில் மண்ணில் இடவும்."
    }
  },
  {
    "id": "beejamrutham",
    "category": "growth",
    "en": {
      "title": "Beejamrutham",
      "summary": "A seed-coating treatment applied before sowing to protect seeds and boost germination.",
      "body": "Materials needed\nCow dung\nCow urine\nLime\nWater\nA handful of soil\nProcedure\nMix all ingredients together.\nLet the mixture stand overnight.\nCoat seeds with it just before sowing.\nTime to ready\nOvernight\nBenefits\nProtects seeds from soil-borne disease\nBoosts germination rates\nHow to use\nCoat seeds immediately before sowing."
    },
    "ta": {
      "title": "பீஜாமிர்தம்",
      "summary": "விதைகளைப் பாதுகாக்கவும் முளைப்பை ஊக்குவிக்கவும் விதைப்பதற்கு முன் பூசப்படும் விதை நேர்த்திப் பொருள்.",
      "body": "தேவையான பொருட்கள்\nமாட்டுச் சாணம்\nமாட்டுச் சிறுநீர்\nசுண்ணாம்பு\nநீர்\nமண் ஒரு கைப்பிடி\nசெய்முறை\nஅனைத்துப் பொருட்களையும் ஒன்றாகக் கலக்கவும்.\nகலவையை இரவு முழுவதும் வைத்திருக்கவும்.\nவிதைப்பதற்கு சற்று முன் விதைகளில் பூசவும்.\nதயாராகும் காலம்\nஒரு இரவு\nநன்மைகள்\nமண் மூலம் பரவும் நோய்களிலிருந்து விதைகளைப் பாதுகாக்கிறது\nமுளைப்பு விகிதத்தை அதிகரிக்கிறது\nபயன்படுத்தும் முறை\nவிதைப்பதற்கு உடனடியாக முன் விதைகளில் பூசவும்."
    }
  },
  {
    "id": "seed-egg-tonic",
    "category": "growth",
    "en": {
      "title": "Sprouted Seed Extract / Egg-Jaggery Tonic",
      "summary": "A fermented natural growth-hormone tonic to improve flowering and fruit-setting.",
      "body": "Materials needed\nSprouted seeds OR egg\nJaggery\nWater\nProcedure\nMix ingredients together.\nFerment for 3–5 days.\nStrain before use.\nTime to ready\n3–5 days\nBenefits\nNatural growth hormone boost\nImproves flowering and fruit-setting\nHow to use\nDilute and apply as a foliar spray."
    },
    "ta": {
      "title": "முளைகட்டிய விதைச் சாறு / முட்டை–வெல்ல டானிக்",
      "summary": "பூத்தலையும் காய் பிடித்தலையும் மேம்படுத்தும் நொதித்த இயற்கை வளர்ச்சி ஹார்மோன் டானிக்.",
      "body": "தேவையான பொருட்கள்\nமுளைகட்டிய விதைகள் அல்லது முட்டை\nவெல்லம்\nநீர்\nசெய்முறை\nபொருட்களை ஒன்றாகக் கலக்கவும்.\n3–5 நாட்கள் நொதிக்க விடவும்.\nபயன்படுத்தும் முன் வடிகட்டவும்.\nதயாராகும் காலம்\n3–5 நாட்கள்\nநன்மைகள்\nஇயற்கை வளர்ச்சி ஹார்மோன் ஊக்கம்\nபூத்தலையும் காய் பிடித்தலையும் மேம்படுத்துகிறது\nபயன்படுத்தும் முறை\nநீர்த்துப்போகச் செய்து இலைவழித் தெளிப்பாகப் பயன்படுத்தவும்."
    }
  },
  {
    "id": "mulching",
    "category": "soil",
    "en": {
      "title": "Mulching",
      "summary": "Covering the soil around plants with crop residue or straw to protect and improve it.",
      "body": "Materials needed\nCrop residue or straw\nProcedure\nSpread a layer of residue around the base of plants after sowing or transplanting.\nTime to ready\nOngoing practice, not a one-time preparation\nBenefits\nRetains soil moisture\nSuppresses weeds\nModerates soil temperature\nHow to use\nApply a 5–10 cm layer around plants."
    },
    "ta": {
      "title": "மூடாக்கு",
      "summary": "தாவரங்களைச் சுற்றியுள்ள மண்ணைப் பாதுகாக்கவும் மேம்படுத்தவும் பயிர்க் கழிவுகள் அல்லது வைக்கோலால் மூடும் முறை.",
      "body": "தேவையான பொருட்கள்\nபயிர்க் கழிவுகள் அல்லது வைக்கோல்\nசெய்முறை\nவிதைத்த அல்லது நடவு செய்த பிறகு தாவரங்களின் அடிப்பகுதியைச் சுற்றி கழிவுகளை ஒரு அடுக்காகப் பரப்பவும்.\nதயாராகும் காலம்\nதொடர்ந்து செய்யும் நடைமுறை; ஒருமுறை தயாரிக்கும் பொருள் அல்ல\nநன்மைகள்\nமண் ஈரப்பதத்தைத் தக்கவைக்கிறது\nகளைகளை அடக்குகிறது\nமண் வெப்பநிலையைச் சீராக்குகிறது\nபயன்படுத்தும் முறை\nதாவரங்களைச் சுற்றி 5–10 செ.மீ. தடிமனான அடுக்காக இடவும்."
    }
  },
  {
    "id": "biochar",
    "category": "soil",
    "en": {
      "title": "Biochar",
      "summary": "Charred (not burned to ash) crop waste that adds stable, long-term carbon to soil.",
      "body": "Materials needed\nCrop waste (stalks, husks, etc.)\nA controlled low-oxygen kiln, pit, or drum\nProcedure\nBurn residue in a low-oxygen setup until charred, not reduced to ash.\nQuench with water to stop the burn at the right point.\nTime to ready\nA few hours per batch\nBenefits\nAdds long-term carbon to soil\nImproves water and nutrient retention\nReduces how often other amendments need reapplying\nHow to use\nMix into soil, ideally activated first with compost or manure."
    },
    "ta": {
      "title": "பயோசார்",
      "summary": "மண்ணில் நீண்டகாலம் நிலைக்கும் கார்பனைச் சேர்க்கும் கரியாக்கப்பட்ட பயிர்க் கழிவு (சாம்பலாக எரிக்கப்பட்டதல்ல).",
      "body": "தேவையான பொருட்கள்\nபயிர்க் கழிவுகள் (தண்டுகள், உமி போன்றவை)\nகட்டுப்படுத்தப்பட்ட குறைந்த ஆக்சிஜன் உலை, குழி அல்லது பீப்பாய்\nசெய்முறை\nகுறைந்த ஆக்சிஜன் அமைப்பில் கழிவுகளை சாம்பலாகாமல் கரியாகும் வரை எரிக்கவும்.\nசரியான நிலையில் எரிவதை நிறுத்த நீர் ஊற்றி அணைக்கவும்.\nதயாராகும் காலம்\nஒரு தொகுதிக்கு சில மணி நேரம்\nநன்மைகள்\nமண்ணில் நீண்டகால கார்பனைச் சேர்க்கிறது\nநீர் மற்றும் ஊட்டச்சத்துப் பிடிப்பை மேம்படுத்துகிறது\nபிற மண் மேம்பாட்டுப் பொருட்களை மீண்டும் இட வேண்டிய இடைவெளியை அதிகரிக்கிறது\nபயன்படுத்தும் முறை\nமண்ணில் கலக்கவும்; முதலில் கம்போஸ்ட் அல்லது எருவுடன் ஊட்டமேற்றுவது சிறந்தது."
    }
  }
];

