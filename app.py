"""Small macOS Tk app. Preview/export run only in monitored subprocesses."""
import os,sys,time,signal,queue,threading,tempfile,subprocess,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from PIL import Image,ImageTk
from engine import EFFECTS
from safety import check_source, publish_no_overwrite, validate_export, validate_print_metadata
from print_export import validate_dpi, print_report

MAX_WORKER_RSS=1_800*1024*1024  # soft threshold, NOT an OS-enforced cap
WORKER=Path(__file__).with_name('worker.py')

def run_worker(source,target,mode,effect,strength,seed,timeout,dpi=300):
    """Best-effort resource watchdog, NOT a sandbox or hard memory limit."""
    import psutil
    cmd=[sys.executable,str(WORKER),'--source',str(source),'--target',str(target),'--mode',mode,
         '--effect',effect,'--strength',str(strength),'--seed',str(seed),'--dpi',str(dpi)]
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONSTARTUP','PYTHONINSPECT'):
        env.pop(key,None)
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       start_new_session=True,env=env,cwd=str(WORKER.parent))
    start=time.monotonic()
    try:
        while p.poll() is None:
            if time.monotonic()-start>timeout:
                raise TimeoutError('Délai de traitement dépassé')
            try:
                proc=psutil.Process(p.pid)
                children=proc.children(recursive=True)
                rss=sum(x.memory_info().rss for x in [proc,*children] if x.is_running())
                if rss>MAX_WORKER_RSS:
                    raise MemoryError('Seuil mémoire de surveillance dépassé (1,8 Gio)')
            except psutil.NoSuchProcess:
                pass
            time.sleep(.12)
        out,err=p.communicate(timeout=5)
        if p.returncode:
            raise RuntimeError(err.decode('utf-8','replace')[-900:] or f'Worker code {p.returncode}')
        return json.loads(out.decode('utf-8'))
    except BaseException:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        try:p.communicate(timeout=5)
        except subprocess.TimeoutExpired:pass
        raise

class App:
    def __init__(self,root):
        self.root=root;root.title('GPU Failure Studio v3 | Simulation');root.geometry('990x780')
        self.source=None;self.busy=False;self.q=queue.Queue();self.preview=None;self.generation=0;self.closed=False
        frame=ttk.Frame(root,padding=14);frame.pack(fill='x')
        ttk.Button(frame,text='1. Ouvrir une copie',command=self.open).pack(side='left',padx=(0,8))
        ttk.Button(frame,text='3. Export TIFF 16 bits',command=lambda:self.export('tiff')).pack(side='left',padx=4)
        ttk.Button(frame,text='Export JPEG 95',command=lambda:self.export('jpeg')).pack(side='left',padx=4)
        settings=ttk.LabelFrame(root,text='2. Simulation',padding=12);settings.pack(fill='x',padx=14,pady=8)
        ttk.Label(settings,text='Anomalie').grid(row=0,column=0,sticky='w')
        self.effect=tk.StringVar(value='Composite failure')
        ttk.Combobox(settings,textvariable=self.effect,values=EFFECTS,state='readonly',width=27).grid(row=0,column=1,padx=8)
        ttk.Label(settings,text='Intensité').grid(row=0,column=2,padx=(10,0))
        self.strength=tk.DoubleVar(value=.45)
        ttk.Scale(settings,from_=0,to=1,variable=self.strength,length=150).grid(row=0,column=3,padx=8)
        ttk.Label(settings,text='Graine').grid(row=0,column=4)
        self.seed=tk.StringVar(value='2026');ttk.Entry(settings,textvariable=self.seed,width=12).grid(row=0,column=5,padx=8)
        ttk.Label(settings,text='Impression (ppp)').grid(row=1,column=0,sticky='w',pady=(8,0))
        self.dpi=tk.StringVar(value='300');ttk.Entry(settings,textvariable=self.dpi,width=10).grid(row=1,column=1,sticky='w',padx=8,pady=(8,0))
        ttk.Button(settings,text='Actualiser aperçu',command=self.refresh).grid(row=0,column=6)
        self.status=tk.StringVar(value='Prêt. Utiliser une copie non confidentielle pour les premiers tests.')
        ttk.Label(root,textvariable=self.status,padding=(14,8),wraplength=900).pack(fill='x')
        self.image=ttk.Label(root,anchor='center');self.image.pack(fill='both',expand=True,padx=14,pady=8)
        ttk.Label(root,text='Simulation CPU uniquement · RAW original jamais écrit · Pas de sandbox macOS · Aucun réseau nécessaire à l’exécution',padding=10).pack()
        root.protocol('WM_DELETE_WINDOW',self.on_close)
        root.after(100,self.poll)
    def on_close(self):
        if self.busy:
            messagebox.showwarning('Traitement actif','Attendre la fin du traitement avant de fermer. Pour un arrêt forcé, fermer le Terminal.')
            return
        self.closed=True
        self.root.destroy()
    def parameters(self):
        seed=int(self.seed.get())
        if not 0<=seed<2**63:raise ValueError('Graine hors limites')
        return self.effect.get(),float(self.strength.get()),seed
    def launch(self,kind,fn):
        if self.busy:return
        self.busy=True;self.status.set('Traitement en cours… Ne pas fermer la fenêtre.')
        def run():
            try:self.q.put((kind,True,fn()))
            except Exception as e:self.q.put((kind,False,str(e)))
        threading.Thread(target=run,daemon=True).start()
    def poll(self):
        try:
            while True:
                kind,ok,val=self.q.get_nowait();self.busy=False
                if not ok:self.status.set('Erreur : '+val);messagebox.showerror('Opération interrompue',val)
                elif kind=='preview':
                    try:
                        with Image.open(val) as im:
                            im.load();self.preview=ImageTk.PhotoImage(im.copy())
                        self.image.configure(image=self.preview);self.status.set('Aperçu simulé prêt. L’export recalcule à pleine résolution.')
                    finally:
                        Path(val).unlink(missing_ok=True)
                else:
                    path, report, icc_status = val
                    details = ('Profil ICC intégré.' if icc_status == 'embedded' else 'ATTENTION : profil ICC inconnu, fidélité colorimétrique non garantie.')
                    if not report['a3_enough_pixels'] or not report['a3_ratio_matches']:
                        details += '\nAttention : dimensions insuffisantes ou ratio différent pour un A3 entier sans recadrage.'
                    self.status.set('Export terminé : '+path)
                    messagebox.showinfo('Export terminé',path+'\n'+details)
        except queue.Empty:pass
        if not self.closed:self.root.after(100,self.poll)
    def open(self):
        if self.busy:return
        path=filedialog.askopenfilename(title='Choisir une copie de photo')
        if not path:return
        try:self.source=check_source(path)
        except Exception as e:messagebox.showerror('Fichier refusé',str(e));return
        self.refresh()
    def refresh(self):
        if self.busy or self.source is None:return
        try:effect,strength,seed=self.parameters()
        except Exception as e:messagebox.showerror('Paramètres',str(e));return
        source=self.source
        def task():
            with tempfile.TemporaryDirectory(prefix='gpu_studio_preview_') as d:
                dest=Path(d)/'preview.png';run_worker(source,dest,'preview',effect,strength,seed,60)
                # read bytes before temporary directory disappears; return stable PNG path
                fd,path=tempfile.mkstemp(prefix='gpu_studio_view_',suffix='.png');os.close(fd)
                try:
                    Path(path).write_bytes(dest.read_bytes());return path
                except BaseException:Path(path).unlink(missing_ok=True);raise
        self.launch('preview',task)
    def export(self,mode):
        if self.busy or self.source is None:return
        try:effect,strength,seed=self.parameters()
        except Exception as e:messagebox.showerror('Paramètres',str(e));return
        ext='.tif' if mode=='tiff' else '.jpg'
        chosen=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[('TIFF 16 bits','*.tif')] if mode=='tiff' else [('JPEG 95','*.jpg')])
        if not chosen:return
        dest=Path(chosen).expanduser().absolute()
        if dest.suffix.lower()!=ext:messagebox.showerror('Export','Extension incorrecte');return
        if dest.exists() or dest.is_symlink():messagebox.showerror('Export','Le fichier existe déjà. Aucun écrasement autorisé.');return
        try:dpi=validate_dpi(int(self.dpi.get()))
        except (ValueError,TypeError) as e:messagebox.showerror('Résolution',str(e));return
        source=self.source
        def task():
            fd,name=tempfile.mkstemp(prefix='.gpu_studio_',suffix=ext,dir=dest.parent);os.close(fd)
            tmp=Path(name)
            try:
                result=run_worker(source,tmp,mode,effect,strength,seed,180,dpi)
                if not tmp.is_file() or tmp.stat().st_size==0:raise ValueError('Export vide')
                validate_export(tmp,mode)
                validate_print_metadata(tmp,mode,dpi,result['icc'])
                # Print metadata only: no pixel enlargement or color-profile conversion.
                publish_no_overwrite(tmp,dest)
                return str(dest),result['print'],result['icc']
            finally:tmp.unlink(missing_ok=True)
        self.launch('export',task)
if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
