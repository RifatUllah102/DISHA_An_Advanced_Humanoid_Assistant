import bangla
from banglanum2words import num_convert
from num2words import num2words

#Convert Bangla Input (Number/Word) to English Number/Word


BanglaNumber = ['০','১','২','৩','৪','৫','৬','৭','৮','৯']
EnglishNumber = ['0','1','2','3','4','5','6','7','8','9']

BanglaWord = ['ওয়াসা', 'ইলেক্ট্রিসিটি', 'টেলিফোন', 'নেট', 'ডিটিএইচ', 'সিএএসএ', 'এফডিআর','লোন', 'ইএমআই', 'সঞ্চয়', 'চলতি', 'বিদ্যুৎ', 'কারেন্ট']
EnglishWord = ['WASA', 'Electricity', 'telephone', 'Internet', 'DTH', 'CASA', 'FDR', 'loan', 'EMI', 'saving', 'current', 'Electricity', 'Electricity']

X = []

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def BnToEn(Input):
  #input = str(Input)
  list_of_letters = list(Input)
  # print(list_of_letters)
  for i in list_of_letters:    
    if(is_ascii(i)):
      X.append(i)
    else:
      X.append(BanglaNumber.index(i))

  # print(X)
  Output = "".join(map(str, X))
  X.clear()
  # print("Output from Converter")
  # print(Output)
  # print(type(Output))
  return Output

def BnToEn_Word(word):
    i=-1
    for w in BanglaWord:
        if(w==word):
            i=BanglaWord.index(word)
    if(i>=0):
        return EnglishWord[i]
    return ''

def amount_in_word(amount):

  tell_amount = amount

  if tell_amount != None:
      bangla_numeric_string = bangla.convert_english_digit_to_bangla_digit(tell_amount)
      print(bangla_numeric_string)
      print(type(bangla_numeric_string))
      print('bangla_numeric_string: ', len(str(bangla_numeric_string)))
      if(len(str(bangla_numeric_string))>8):
          amount=bangla_numeric_string
          return amount
      else:
          amount = num_convert.number_to_bangla_words(bangla_numeric_string)
          return amount

def numberTranslate(getnumber):
  tell_Number = getnumber
  number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']

  if(tell_Number!=None):
      wr=''
      for c in tell_Number:
          wr=wr+' '+number[int(c)]

  wr2 = wr.split(" ")
  for i in range(len(wr2)):
      wr2[i] = wr2[i]+","
  wr = ' '.join(wr2)
  return wr