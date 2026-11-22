"""Runs a fixed Turkish question set through brain.py (no web sources) and prints kind + answer.
python eval_questions.py [data/wiki.db]"""
import sys, time
from brain import Brain
from search import WikiIndex
from lm import AlperLM

QS = ["Merhaba", "Sen kimsin?", "Gemini misin?", "Bugün günlerden ne?", "125*8+3 kaç eder?",
      "Atatürk kimdir?", "Atatürk ne zaman doğdu?", "Mimar Sinan kimdir?", "Nazım Hikmet kimdir?",
      "Everest Dağı'nın yüksekliği kaç metre?", "Türkiye'nin en yüksek dağı hangisidir?", "Dünyanın en büyük okyanusu hangisidir?",
      "Ay'ın Dünya'ya uzaklığı ne kadar?", "Ankara'nın nüfusu kaç?", "Almanya'nın başkenti neresidir?",
      "Türkiye'nin başkenti neresidir?", "Fransa'nın başkenti neresi?", "Japonya'nın başkenti neresidir?",
      "İstanbul'un fethi hangi yılda oldu?", "Kurtuluş Savaşı ne zaman bitti?", "Fotosentez nedir?",
      "Python programlama dili nedir?", "Kuantum bilgisayar nedir?", "Dünyanın en uzun nehri hangisidir?",
      "Su kaç derecede kaynar?", "Einstein hangi teoriyi geliştirdi?", "Bitcoin fiyatı bugün kaç dolar?",
      "Yusuf'un en sevdiği renk ne?", "Bana kısa bir şiir yaz"]
db = sys.argv[1] if len(sys.argv) > 1 else 'data/wiki.db'
br = Brain(WikiIndex(db), AlperLM('model/alper.pt', 'model/tokenizer.json'))
for q in QS:
    t = time.time()
    a = br.answer([{'role': 'user', 'content': q}])
    text = a.text if a.stream is None else ''.join(a.stream(None)) + a.text
    print(f'### {q}\n[{a.kind}] ({(time.time()-t)*1000:.0f} ms) ' + ' '.join(text.split())[:330] + '\n')
