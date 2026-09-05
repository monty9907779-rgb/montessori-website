import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";

type PageCopy = {
  title: string;
  description: string;
  intro: string;
  sections: { heading: string; body: string }[];
  faq: { question: string; answer: string }[];
  related: { href: string; label: string }[];
};

type Locale = "ar" | "en";

const localeSlugs: Record<Locale, readonly string[]> = {
  ar: ["hadana-qariba-minni", "kayfa-akhtar-hadana", "rsum-alhadanat-fi-jeddah", "what-is-montessori-method"],
  en: ["daycare-near-me-jeddah", "preschool-near-me-jeddah", "kindergarten-near-me-jeddah", "what-is-montessori-method"],
};

const keywordMap: Record<Locale, Record<string, string[]>> = {
  ar: {
    "hadana-qariba-minni": ["حضانة قريبة مني", "حضانة اطفال جدة", "حضانة مونتيسوري جدة", "حضانة في جدة", "حضانة حي الشاطئ"],
    "kayfa-akhtar-hadana": ["كيف أختار حضانة", "أفضل حضانة في جدة", "اختيار حضانة للأطفال"],
    "rsum-alhadanat-fi-jeddah": ["رسوم الحضانات في جدة", "أسعار الحضانات في جدة", "رسوم الحضانة", "حضانة يوم كامل جدة", "حضانة بالساعة في جدة"],
    "what-is-montessori-method": ["ما هو منهج مونتيسوري", "مركز اطفال مونتيسوري", "مونتيسوري للاطفال"],
  },
  en: {
    "daycare-near-me-jeddah": ["daycare near me", "daycare in Jeddah", "best daycare in Jeddah", "Montessori daycare Jeddah"],
    "preschool-near-me-jeddah": ["preschool near me", "Montessori preschool near me", "nursery schools near me", "preschool in Jeddah"],
    "kindergarten-near-me-jeddah": ["kindergarten near me", "kindergarten in Jeddah", "Montessori kindergarten Jeddah"],
    "what-is-montessori-method": ["what is the Montessori method", "Montessori nursery Jeddah", "Montessori early education"],
  },
};

function getPageCopy(locale: string, slug: string): PageCopy | undefined {
  if (!Object.prototype.hasOwnProperty.call(localeSlugs, locale)) return undefined;
  const typedLocale = locale as Locale;
  if (!localeSlugs[typedLocale].includes(slug)) return undefined;
  return locale === "en" && slug === "what-is-montessori-method"
    ? englishMontessoriPage
    : pages[slug];
}

const equivalentSlugs: Partial<Record<string, string>> = {
  "hadana-qariba-minni": "daycare-near-me-jeddah",
  "daycare-near-me-jeddah": "hadana-qariba-minni",
  "what-is-montessori-method": "what-is-montessori-method",
};

const pages: Record<string, PageCopy> = {
  "hadana-qariba-minni": {
    title: "حضانة قريبة مني في جدة",
    description: "دليل عملي للعثور على حضانة آمنة وقريبة في جدة، مع معلومات عن البرامج المونتيسورية والتواصل مع حضانة كوكب الطفل الحر.",
    intro: "إذا كنت تبحث عن حضانة قريبة منك في جدة، فالقرب مهم، لكنه ليس المعيار الوحيد. ابدأ بالموقع، ثم تحقق من السلامة، خبرة الفريق، البرنامج اليومي، وطريقة تواصل الحضانة مع الأسرة.",
    sections: [
      { heading: "ماذا تتحقق منه قبل التسجيل؟", body: "اسأل عن الترخيص، نسبة المعلمات إلى الأطفال، إجراءات الاستلام والانصراف، النظافة، المساحات الداخلية والخارجية، وآلية التعامل مع الحالات الصحية والطوارئ." },
      { heading: "برامج تناسب مراحل النمو", body: "تقدم حضانة كوكب الطفل الحر برامج للأطفال من عمر 3 أشهر إلى 6 سنوات، تشمل نيدو للرضع، وبرنامج الأطفال الصغار، وبيت الأطفال، والتهيئة المدرسية. اسأل الفريق عن البرنامج الأنسب لعمر طفلك واستعداده." },
      { heading: "الرعاية بالساعة أو اليوم الكامل", body: "إذا كنت تحتاج إلى حضانة بالساعة أو رعاية يوم كامل، اطلب من الفريق توضيح الخيارات المتاحة، أوقات الاستقبال والانصراف، وما يتضمنه كل نظام قبل التسجيل. لا تعتمد على إعلان قديم أو سعر غير مؤكد." },
      { heading: "اللغة والسلامة والتواصل مع الأسرة", body: "تأكد من وجود تعرض عربي وإنجليزي مناسب لاحتياجات طفلك، ومن وضوح إجراءات الاستلام والطوارئ والنظافة. اسأل كيف تُشارك الحضانة الملاحظات اليومية والتقدم مع الأسرة." },
      { heading: "الموقع وساعات العمل", body: "تقع الروضة في حي الشاطئ في جدة، وتستقبل الأسر من الأحد إلى الخميس من ٧:٣٠ صباحًا حتى ٣:٠٠ مساءً. استخدم رابط خرائط جوجل في قسم التواصل للتحقق من الاتجاهات قبل الزيارة." },
      { heading: "الرسوم وخطوات القبول", body: "اطلب الرسوم الحالية كتابةً، وما إذا كانت تشمل الوجبات أو المواد أو التسجيل، ثم تحقق من المستندات المطلوبة والطاقة الاستيعابية وموعد بدء الطفل. التفاصيل تتغير، لذلك الأفضل تأكيدها مباشرة مع الحضانة." },
    ],
    faq: [
      { question: "هل الحضانة القريبة أفضل دائمًا؟", answer: "القرب يسهل الروتين اليومي والطوارئ، لكنه يجب أن يأتي مع بيئة آمنة وفريق مؤهل وبرنامج مناسب لعمر الطفل." },
      { question: "ما الأعمار التي تستقبلها الحضانة؟", answer: "تستقبل البرامج الأطفال من عمر 3 أشهر حتى 6 سنوات، حسب البرنامج والطاقة الاستيعابية المتاحة." },
    ],
    related: [
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
      { href: "/ar/rsum-alhadanat-fi-jeddah", label: "رسوم الحضانات في جدة" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  "kayfa-akhtar-hadana": {
    title: "كيف أختار حضانة لطفلي في جدة؟",
    description: "خطوات عملية لاختيار حضانة مناسبة وآمنة في جدة، من مقارنة البيئة والبرامج إلى التحقق من التواصل والرسوم قبل التسجيل.",
    intro: "اختيار الحضانة قرار يومي يهم راحة الطفل والأسرة معًا. قارِن بين الموقع، البيئة، الفريق، البرنامج، وساعات العمل، ثم اتخذ القرار بعد زيارة المكان وطرح أسئلة محددة.",
    sections: [
      { heading: "ابدأ بالموقع والروتين اليومي", body: "اختر موقعًا يناسب طريق الأسرة، ثم تحقق من أوقات الوصول والانصراف، سياسة التأخير، وإجراءات تسليم الطفل للأشخاص المصرح لهم. سهولة الروتين تساعد على الاستمرار وتقلل الضغط." },
      { heading: "افحص البيئة والفريق", body: "لاحظ ترتيب الفصول، النظافة، سلامة الأدوات، مساحة الحركة، وطريقة حديث المعلمات مع الأطفال. اسأل عن تدريب الفريق، نسبة الأطفال إلى المعلمات، وكيفية دعم احتياجات كل عمر." },
      { heading: "قارن البرنامج بما يحتاجه طفلك", body: "اسأل عن الأعمار والبرامج، وقت العمل المستقل، الأنشطة الحركية واللغوية، الراحة، الوجبات، والتعرض العربي والإنجليزي. البرنامج الجيد يوازن بين الاستقلالية، التعلم العملي، واللعب الهادف." },
      { heading: "اطلب معلومات القبول والرسوم", body: "قبل اتخاذ القرار، اطلب الرسوم الحالية، أوقات الدوام، المستندات المطلوبة، سياسة الغياب، وطريقة تأكيد المقعد. لا تعتمد على أسعار أو مواعيد غير محدثة من منشور قديم." },
      { heading: "زر المكان وتواصل مع الأسرة", body: "زيارة الحضانة في ساعات العمل تكشف تفاصيل لا تظهر في الصور. اسأل كيف يتابع الفريق تقدم الطفل، وكيف يتواصل مع الأسرة عند المرض أو الطوارئ، وما هي قنوات التواصل اليومية." },
    ],
    faq: [
      { question: "ما أهم سؤال أطرحه في زيارة الحضانة؟", answer: "اسأل كيف يبدو اليوم العادي لطفلك، ومن سيتولى رعايته، وكيف تتعامل الحضانة مع الاستلام والمرض والطوارئ والتواصل مع الأسرة." },
      { question: "هل أختار الحضانة الأقرب لمنزلي؟", answer: "القرب عامل مهم، لكنه يجب أن يُقارن بالسلامة، جودة الفريق، ملاءمة البرنامج، ساعات العمل، ووضوح الرسوم والسياسات." },
    ],
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/rsum-alhadanat-fi-jeddah", label: "رسوم الحضانات في جدة" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  "rsum-alhadanat-fi-jeddah": {
    title: "رسوم الحضانات في جدة: ما الذي يجب أن تعرفه قبل التسجيل؟",
    description: "دليل عملي لفهم رسوم الحضانات في جدة ومقارنة الدوام الكامل والدوام الجزئي والرعاية بالساعة وما يشمله التسجيل.",
    intro: "تختلف رسوم الحضانات في جدة حسب عمر الطفل، عدد الساعات، البرنامج، الوجبات، والخدمات الإضافية. استخدم هذا الدليل لطلب عرض واضح ومقارنة الخيارات قبل حجز المقعد.",
    sections: [
      { heading: "ما الذي يحدد الرسوم؟", body: "اسأل عن عمر الطفل والبرنامج المناسب له، عدد أيام الحضور، ساعات الدوام، مدة الفصل أو الشهر، وهل تختلف الرسوم بين الرضع والأطفال الصغار وبيت الأطفال والتهيئة المدرسية." },
      { heading: "دوام كامل أم جزئي؟", body: "اطلب توضيح الفرق بين الدوام الكامل والدوام الجزئي، وما إذا كان المقعد ثابتًا طوال الأسبوع. قارن ساعات الرعاية الفعلية مع احتياج أسرتك بدل مقارنة رقم شهري فقط." },
      { heading: "الرعاية بالساعة", body: "إذا كنت تبحث عن حضانة بالساعة في جدة، اسأل عن توفر هذا الخيار، الحد الأدنى للساعات، الحجز المسبق، أوقات الاستلام والانصراف، وما إذا كانت الرعاية بالساعة متاحة لكل الأعمار." },
      { heading: "ما الذي قد يشمله السعر؟", body: "تحقق كتابةً من شمول التسجيل، المواد التعليمية، الوجبات، وقت الراحة، الأنشطة، الزي، أو أي خدمة نقل. لا تفترض أن هذه البنود مشمولة ما لم تُذكر في العرض الحالي." },
      { heading: "الخصومات والرسوم الإضافية", body: "اسأل عن خصم الإخوة، خصم الفصل أو السداد المقدم، رسوم التسجيل، التأمين أو حجز المقعد، وسياسة الاسترداد والغياب. اطلب إجمالي التكلفة وتاريخ سريانها بوضوح." },
      { heading: "كيف تطلب عرضًا مناسبًا؟", body: "تواصل مع حضانة كوكب الطفل الحر واذكر عمر الطفل، البرنامج المتوقع، عدد الأيام، واحتياجك للدوام الكامل أو الجزئي. سيؤكد الفريق الخيارات المتاحة والرسوم الحالية قبل التسجيل." },
    ],
    faq: [
      { question: "كم تبلغ رسوم الحضانات في جدة؟", answer: "لا يوجد سعر واحد يناسب كل الحضانات؛ تختلف التكلفة حسب العمر والبرنامج وعدد الساعات والخدمات. اطلب السعر الحالي مباشرة من الحضانة قبل اتخاذ القرار." },
      { question: "هل توجد حضانة يوم كامل في جدة؟", answer: "تختلف خيارات الدوام الكامل حسب الحضانة والطاقة الاستيعابية. أكّد ساعات الدوام، الأيام، وما يشمله النظام مع الفريق قبل حجز المقعد." },
      { question: "هل تشمل الرسوم الوجبات والمواد؟", answer: "قد تختلف البنود المشمولة من برنامج إلى آخر. اطلب قائمة مكتوبة توضح التسجيل والمواد والوجبات وأي رسوم إضافية." },
    ],
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  "daycare-near-me-jeddah": {
    title: "Daycare Near Me in Jeddah",
    description: "A practical guide to finding safe, convenient daycare near you in Jeddah and learning about Montessori childcare programs.",
    intro: "When searching for daycare near you in Jeddah, location is only the first filter. Compare safety routines, staff qualifications, age groups, daily communication, and the learning environment before enrolling.",
    sections: [
      { heading: "What to check before enrollment", body: "Ask about licensing, child-to-educator ratios, arrival and pickup procedures, hygiene, outdoor time, meals, and how the nursery handles illness and emergencies." },
      { heading: "Programs and ages", body: "Planet of the Free Child Nursery serves children from 3 months to 6 years in Jeddah through infant, toddler, Children's House, and school-preparation programs. Ask the team which program matches your child's age and readiness." },
      { heading: "Hourly and full-day daycare", body: "If you need hourly care or a full-day arrangement, ask the nursery to confirm the current options, arrival and pickup windows, inclusions, and availability. Treat older social posts and unconfirmed prices as out of date." },
      { heading: "Bilingual care and safety routines", body: "Ask how Arabic-English exposure is integrated into the day, how authorized pickup is managed, and how the team handles hygiene, illness, allergies, and emergencies. Clear daily updates help families stay informed." },
      { heading: "Hours and location", body: "The nursery is in Jeddah's Al Shati District and is open Sunday through Thursday from 7:30 AM to 3:00 PM. Use the Google Maps link in the contact section to confirm directions before your visit." },
      { heading: "Fees and enrollment documents", body: "Request current fees in writing and confirm what is included, which documents are required, how a place is reserved, and when your child can start. These details should be verified directly with the nursery." },
      { heading: "Book a visit", body: "A visit during operating hours helps you assess the atmosphere, observe educator-child interactions, and receive clear information about schedules, fees, and availability." },
    ],
    faq: [
      { question: "Is the closest daycare always the best choice?", answer: "Proximity makes daily routines easier, but safety, qualified educators, and a suitable program should guide the final decision." },
      { question: "What ages are accepted?", answer: "Programs are available for children from 3 months to 6 years, subject to the selected program and availability." },
    ],
    related: [
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  "preschool-near-me-jeddah": {
    title: "Preschool Near Me in Jeddah",
    description: "Compare preschool options in Jeddah and discover a bilingual Montessori environment for early learning and independence.",
    intro: "A strong preschool gives children time to build language, movement, concentration, independence, and social confidence. In Jeddah, families can compare location and convenience with the quality of the prepared environment.",
    sections: [
      { heading: "What makes a preschool supportive?", body: "Look for calm classrooms, accessible materials, a predictable rhythm, purposeful activities, outdoor movement, and educators who observe each child instead of using one pace for everyone." },
      { heading: "Montessori preschool ages and programs", body: "Planet of the Free Child serves children from 3 months to 6 years with bilingual Arabic-English exposure and Montessori-inspired developmental programs. Ask about the daily rhythm, group size, and transition between age groups." },
      { heading: "Bilingual learning and school readiness", body: "Children can build practical skills, communication, early literacy, numeracy, concentration, and cooperation through hands-on work. Ask how the team records progress and supports the move to primary school." },
      { heading: "Hours, meals, and family communication", body: "Confirm the current Sunday-to-Thursday schedule, arrival and pickup process, meal and allergy arrangements, rest time, and how updates are shared with families. Written details make preschool options easier to compare." },
      { heading: "A practical visit checklist", body: "During a visit, observe the prepared environment, the materials at the child's level, educator-child interactions, opportunities for movement, and the way children return work to its place. Then request current fees and enrollment requirements." },
    ],
    faq: [
      { question: "What age does preschool usually start?", answer: "Preschool commonly begins around age 2 or 3, but the right start depends on the child's readiness and the program offered." },
      { question: "Is Montessori suitable for preschool children?", answer: "Montessori is designed around children's developmental needs and uses hands-on materials, choice within limits, and progressive independence." },
    ],
    related: [
      { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
      { href: "/en/kindergarten-near-me-jeddah", label: "Kindergarten Near Me in Jeddah" },
    ],
  },
  "kindergarten-near-me-jeddah": {
    title: "Kindergarten Near Me in Jeddah",
    description: "Find a kindergarten near you in Jeddah and compare Montessori kindergarten preparation, bilingual learning, and family communication.",
    intro: "Choosing a kindergarten in Jeddah means looking beyond a convenient address. Families should compare the learning approach, classroom environment, school-readiness goals, and how educators share progress.",
    sections: [
      { heading: "A balanced kindergarten environment", body: "Children need a balance of focused work, movement, practical life, language, mathematics, creative expression, and opportunities to cooperate with peers." },
      { heading: "Montessori preparation", body: "A Montessori classroom supports concentration, orderly movement, independence, early literacy, numeracy, and responsibility through carefully sequenced materials." },
      { heading: "Bilingual curriculum and school readiness", body: "Ask how Arabic-English exposure, early literacy, numeracy, practical life, movement, and social development are balanced across the day. A clear progression helps families understand how the program prepares children for the next stage." },
      { heading: "Safety, meals, and enrollment", body: "Confirm authorized pickup, illness and emergency procedures, allergies, meals, rest, current hours, fees, required documents, and the process for checking availability. Request the current details directly from the kindergarten." },
      { heading: "Questions for your visit", body: "Ask how the classroom supports different abilities, how progress is documented, what the daily schedule looks like, how parents communicate with the team, and how the child is supported during transitions." },
    ],
    faq: [
      { question: "How do I compare kindergartens?", answer: "Visit more than one setting and compare safety, educators, classroom practice, communication, schedule, fees, and the child's response to the environment." },
      { question: "Does Montessori prepare children for primary school?", answer: "A well-run Montessori program builds academic foundations alongside independence, communication, self-regulation, and social readiness." },
    ],
    related: [
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  "what-is-montessori-method": {
    title: "ما هو منهج مونتيسوري؟",
    description: "تعرف على مبادئ منهج مونتيسوري، دور البيئة المعدة، ودور المعلمة في دعم استقلال الطفل والتعلم المبكر.",
    intro: "منهج مونتيسوري هو نهج في التعليم المبكر يضع الطفل في قلب عملية التعلم. يتعلم الطفل من خلال بيئة معدة، ومواد حسية، واختيار منظم، وتدخل هادف من المعلمة في الوقت المناسب.",
    sections: [
      { heading: "المبادئ الأساسية", body: "يركز المنهج على احترام إيقاع الطفل، التعلم العملي، تنمية التركيز، الاستقلالية، الحركة الهادفة، والفصل المختلط الأعمار عندما تسمح البيئة بذلك." },
      { heading: "دور المعلمة", body: "المعلمة تلاحظ الطفل وتقدم عرضًا واضحًا للمادة، ثم تمنحه وقتًا للعمل والتكرار. الهدف ليس ترك الطفل بلا توجيه، بل تقديم التوجيه المناسب دون إلغاء مبادرته." },
      { heading: "كيف يختار الأهل حضانة مونتيسوري؟", body: "اسأل عن تدريب الفريق، طبيعة المواد، حجم الفصل، وقت العمل المستقل، طريقة متابعة التقدم، وكيف تتواصل الحضانة مع الأسرة." },
    ],
    faq: [
      { question: "هل مونتيسوري يعني اللعب طوال اليوم؟", answer: "يتضمن التعلم حركة واستكشافًا، لكنه يعتمد أيضًا على أعمال مقصودة ومواد مرتبة تساعد الطفل على بناء مهارات محددة." },
      { question: "هل يوجد تعليم عربي وإنجليزي؟", answer: "تقدم حضانة كوكب الطفل الحر بيئة ثنائية اللغة العربية والإنجليزية ضمن برامجها التعليمية." },
    ],
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
    ],
  },
};

const englishMontessoriPage: PageCopy = {
  title: "What Is the Montessori Method?",
  description: "Learn the principles of the Montessori method, the prepared environment, and how educators support independence in early childhood.",
  intro: "The Montessori method is an approach to early education that places the child at the center of learning. Children work in a prepared environment with hands-on materials, meaningful choice, and timely guidance from the educator.",
  sections: [
    { heading: "Core principles", body: "The method respects each child's pace and emphasizes hands-on learning, concentration, independence, purposeful movement, and mixed-age communities when the setting supports them." },
    { heading: "The educator's role", body: "The educator observes the child, gives a clear presentation of a material, and then allows time for practice and repetition. The goal is thoughtful guidance without taking away the child's initiative." },
    { heading: "How to choose a Montessori nursery", body: "Ask about staff training, the quality and sequence of materials, class size, uninterrupted work periods, progress tracking, and communication with families." },
  ],
  faq: [
    { question: "Does Montessori mean children play all day?", answer: "Children move and explore, but the environment also includes purposeful work with materials designed to develop specific skills." },
    { question: "Is Arabic and English learning available?", answer: "Planet of the Free Child Nursery offers Arabic-English bilingual exposure within its educational programs." },
  ],
  related: [
    { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
    { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
  ],
};

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    localeSlugs[locale as Locale].map((slug) => ({ locale, slug }))
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = getPageCopy(locale, slug);
  if (!page) return {};
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://montessori-ksa.com";
  const alternateSlug = equivalentSlugs[slug];
  const languages = alternateSlug
    ? {
        "ar-SA": `${siteUrl}/ar/${locale === "ar" ? slug : alternateSlug}`,
        "en-US": `${siteUrl}/en/${locale === "en" ? slug : alternateSlug}`,
        "x-default": `${siteUrl}/ar/${locale === "ar" ? slug : alternateSlug}`,
      }
    : undefined;
  return {
    title: page.title,
    description: page.description,
    keywords: keywordMap[locale as Locale]?.[slug],
    alternates: {
      canonical: `${siteUrl}/${locale}/${slug}`,
      ...(languages ? { languages } : {}),
    },
    openGraph: { title: page.title, description: page.description, url: `${siteUrl}/${locale}/${slug}`, type: "article" },
  };
}

export default async function SeoPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const page = getPageCopy(locale, slug);
  if (!page) notFound();
  const isAr = locale === "ar";
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://montessori-ksa.com";
  const canonicalUrl = `${siteUrl}/${locale}/${slug}`;
  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Article",
        "@id": `${canonicalUrl}#article`,
        headline: page.title,
        description: page.description,
        inLanguage: locale,
        author: { "@type": "Organization", name: "Planet of the Free Child Nursery" },
        publisher: { "@type": "Organization", name: "Planet of the Free Child Nursery" },
        mainEntityOfPage: { "@type": "WebPage", "@id": canonicalUrl },
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: isAr ? "الرئيسية" : "Home", item: `${siteUrl}/${locale}` },
          { "@type": "ListItem", position: 2, name: page.title, item: canonicalUrl },
        ],
      },
      ...(page.faq.length > 0
        ? [{
            "@type": "FAQPage",
            "@id": `${canonicalUrl}#faq`,
            mainEntity: page.faq.map((item) => ({
              "@type": "Question",
              name: item.question,
              acceptedAnswer: { "@type": "Answer", text: item.answer },
            })),
          }]
        : []),
    ],
  };

  return (
    <main dir={isAr ? "rtl" : "ltr"} className="pt-28 pb-20">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      <article className="max-w-4xl mx-auto px-4 md:px-8">
        <nav aria-label={isAr ? "مسار الصفحة" : "Breadcrumb"} className="mb-7 text-sm text-gray-500">
          <Link href={`/${locale}`} className="hover:text-[#2d5016] hover:underline">
            {isAr ? "الرئيسية" : "Home"}
          </Link>
          <span aria-hidden="true" className="mx-2">/</span>
          <span aria-current="page">{page.title}</span>
        </nav>
        <p className="badge w-fit" style={{ background: "#e9f3dc", color: "#2d5016" }}>
          {isAr ? "دليل مونتيسوري وتعليم مبكر" : "Montessori & Early Education Guide"}
        </p>
        <h1 className="text-4xl md:text-5xl font-black text-gray-900 mt-5 mb-6">{page.title}</h1>
        <p className="text-xl leading-relaxed text-gray-600 mb-12">{page.intro}</p>
        <div className="space-y-10">
          {page.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="text-2xl font-bold text-[#2d5016] mb-3">{section.heading}</h2>
              <p className="text-gray-700 leading-8">{section.body}</p>
            </section>
          ))}
        </div>
        <section className="mt-14 border-t border-gray-200 pt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">{isAr ? "أسئلة شائعة" : "Frequently Asked Questions"}</h2>
          <div className="space-y-6">
            {page.faq.map((item) => (
              <div key={item.question}>
                <h3 className="font-bold text-gray-900 mb-2">{item.question}</h3>
                <p className="text-gray-600 leading-7">{item.answer}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="mt-14 rounded-lg bg-[#f7faf3] p-6">
          <h2 className="text-xl font-bold text-[#2d5016] mb-4">{isAr ? "اقرأ أيضًا" : "Read Next"}</h2>
          <div className="flex flex-wrap gap-3">
            {page.related.map((item) => (
              <Link key={item.href} href={item.href} className="text-[#2d5016] underline underline-offset-4">
                {item.label}
              </Link>
            ))}
            <Link href={`/${locale}#contact`} className="text-[#2d5016] underline underline-offset-4">
              {isAr ? "تواصل مع الحضانة" : "Contact the nursery"}
            </Link>
            <Link href={`/${locale}#programs`} className="text-[#2d5016] underline underline-offset-4">
              {isAr ? "تعرّف على البرامج" : "Explore programs"}
            </Link>
            <Link href={`/${locale}#gallery`} className="text-[#2d5016] underline underline-offset-4">
              {isAr ? "شاهد البيئة التعليمية" : "View the learning environment"}
            </Link>
          </div>
        </section>
      </article>
    </main>
  );
}
