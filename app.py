import os, tempfile, subprocess, json, re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, Response
from openai import OpenAI

app = FastAPI(title='SRT Mobile')
MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB', '100')) * 1024 * 1024
LANGS = {'vi':'Vietnamese','en':'English','pt':'Portuguese','zh':'Chinese','es':'Spanish','ja':'Japanese','ko':'Korean','fr':'French','de':'German','th':'Thai','id':'Indonesian'}

def stamp(seconds):
    ms = max(0, round(float(seconds)*1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms,60000); s, ms = divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def clean(s):
    return re.sub(r'\s+', ' ', str(s)).strip()

def srt(segments):
    return '\n\n'.join(f"{i}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['text']}" for i,x in enumerate(segments,1))+'\n'

@app.get('/',response_class=HTMLResponse)
def home():
    return Path(__file__).with_name('index.html').read_text(encoding='utf-8')

@app.post('/api/process')
async def process(file:UploadFile=File(...), target:str=Form('pt'), source:str=Form('auto')):
    if target not in LANGS: raise HTTPException(400,'Ngôn ngữ đích không hợp lệ')
    if source != 'auto' and source not in LANGS: raise HTTPException(400,'Ngôn ngữ gốc không hợp lệ')
    if not os.getenv('OPENAI_API_KEY'): raise HTTPException(503,'Máy chủ chưa cấu hình OPENAI_API_KEY')
    ext = Path(file.filename or 'video.mp4').suffix.lower()
    if ext not in {'.mp4','.mov','.m4v','.mp3','.m4a','.wav','.webm','.mpeg','.mpga'}: raise HTTPException(400,'Định dạng chưa hỗ trợ')
    client=OpenAI()
    with tempfile.TemporaryDirectory() as folder:
        original=Path(folder)/('input'+ext)
        count=0
        with original.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                count+=len(chunk)
                if count>MAX_BYTES: raise HTTPException(413,'Video vượt dung lượng cho phép')
                out.write(chunk)
        audio=Path(folder)/'audio.mp3'
        try:
            subprocess.run(['ffmpeg','-nostdin','-y','-i',str(original),'-vn','-ac','1','-ar','16000','-b:a','48k',str(audio)],capture_output=True,check=True,timeout=180)
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired): raise HTTPException(422,'Không đọc được âm thanh video')
        if audio.stat().st_size>24*1024*1024: raise HTTPException(413,'Âm thanh quá dài; hãy chia video thành đoạn ngắn')
        kwargs={'model':'whisper-1','response_format':'verbose_json','timestamp_granularities':['segment']}
        if source!='auto':kwargs['language']=source
        with audio.open('rb') as stream:
            result=client.audio.transcriptions.create(file=stream,**kwargs)
        segments=[{'start':float(x.start),'end':float(x.end),'text':clean(x.text)} for x in result.segments if clean(x.text)]
        if not segments: raise HTTPException(422,'Không nhận diện được lời nói')
        translated=[]
        for offset in range(0,len(segments),40):
            batch=segments[offset:offset+40]
            payload=[{'id':offset+i,'text':x['text']} for i,x in enumerate(batch)]
            completion=client.chat.completions.create(model=os.getenv('TRANSLATE_MODEL','gpt-4o-mini'),temperature=0,response_format={'type':'json_object'},messages=[{'role':'system','content':f'Translate each subtitle text into {LANGS[target]}. Return ONLY JSON object with key "items", array of objects with integer id and translated string text. Preserve all IDs, order, meaning, proper nouns. No commentary.'},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}])
            try:
                items=json.loads(completion.choices[0].message.content)['items']
                by_id={int(item['id']):clean(item['text']) for item in items}
                translated.extend([{'start':x['start'],'end':x['end'],'text':by_id[offset+i]} for i,x in enumerate(batch)])
            except (ValueError,KeyError,TypeError): raise HTTPException(502,'Lỗi định dạng bản dịch, hãy thử lại')
        return {'original':srt(segments),'translated':srt(translated),'count':len(segments),'target':target}
