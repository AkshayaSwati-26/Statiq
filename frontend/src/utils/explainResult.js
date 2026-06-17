import { LANGS } from '../hooks/useLang'

export const FORMULAS = {
  employment_rate:   'Employment Rate = (Employed Persons ÷ Total Labour Force) × 100',
  unemployment_rate: 'Unemployment Rate = (Unemployed Persons ÷ Total Labour Force) × 100',
  lfpr:              'Labour Force Participation Rate = (Labour Force ÷ Working Age Population) × 100',
  wpr:               'Worker Population Ratio = (Workers ÷ Total Population) × 100',
  consumption:       'Average MPCE = Total Consumption Expenditure ÷ Number of Households',
  default:           'Weighted Rate = Σ(Value × Survey Weight) ÷ Σ(Survey Weight)',
}

export const FORMULAS_HI = {
  employment_rate:   'रोजगार दर = (रोजगार प्राप्त व्यक्ति ÷ कुल श्रम बल) × 100',
  unemployment_rate: 'बेरोजगारी दर = (बेरोजगार व्यक्ति ÷ कुल श्रम बल) × 100',
  lfpr:              'श्रम बल भागीदारी दर = (श्रम बल ÷ कार्य आयु जनसंख्या) × 100',
  wpr:               'श्रमिक जनसंख्या अनुपात = (श्रमिक ÷ कुल जनसंख्या) × 100',
  default:           'भारित दर = Σ(मूल्य × सर्वेक्षण भार) ÷ Σ(सर्वेक्षण भार)',
}

export function getFormula(indicator, lang = 'en') {
  if (!indicator) return lang === 'hi' ? FORMULAS_HI.default : FORMULAS.default
  const key = indicator.toLowerCase().replace(/ /g, '_')
  const bank = lang === 'hi' ? FORMULAS_HI : FORMULAS
  return bank[key] || bank.default
}

export function generateExplanation(data, indicatorName, lang = 'en') {
  if (!data || data.length === 0) {
    return lang === 'hi'
      ? 'इस प्रश्न के लिए कोई डेटा नहीं मिला। कृपया फ़िल्टर बदलें।'
      : 'No data was returned for this query. Try adjusting your filters.'
  }

  const sorted = [...data].sort((a, b) => b.value - a.value)
  const top    = sorted[0]
  const bottom = sorted[sorted.length - 1]
  const avg    = (data.reduce((s, d) => s + d.value, 0) / data.length).toFixed(1)
  const name   = indicatorName || (lang === 'hi' ? 'चयनित संकेतक' : 'the selected indicator')

  if (lang === 'hi') {
    return `${top.name} में ${name} सबसे अधिक ${top.value}% है, जबकि ${bottom.name} में सबसे कम ${bottom.value}% है। अपलोड किए गए डेटासेट में ${data.length} क्षेत्रों का औसत ${avg}% है।`
  }

  return `${top.name} has the highest ${name} at ${top.value}%, while ${bottom.name} has the lowest at ${bottom.value}%. The average across ${data.length} regions in your uploaded dataset is ${avg}%.`
}