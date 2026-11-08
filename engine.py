"""Deterministic RGB uint16 visual fault effects. No GPU access."""
import numpy as np
EFFECTS=['VRAM blocks','Scanlines','RGB misalignment','GPU tiles','Bit flips','Memory stride','Texture repetition','Pipeline quantization','Shader fault','Framebuffer dropout','Demosaic mosaic','Composite failure']

def simulate(image, effect, strength, seed):
    a=np.array(image,dtype=np.uint16,copy=True)
    if a.ndim!=3 or a.shape[2]!=3: raise ValueError('Expected RGB image')
    h,w,_=a.shape
    if not h or not w: raise ValueError('Empty image')
    rng=np.random.default_rng(int(seed)); s=float(np.clip(strength,0,1))
    if not s:return a
    def apply(name):
        nonlocal a
        if name=='VRAM blocks':
            for _ in range(int(3+60*s)):
                bw=min(w,max(1,int(rng.uniform(.003,.11)*w*s)));bh=min(h,max(1,int(rng.uniform(.002,.09)*h*s)))
                x=int(rng.integers(0,w-bw+1));y=int(rng.integers(0,h-bh+1))
                a[y:y+bh,x:x+bw]=rng.integers(0,65536,size=(1,1,3),dtype=np.uint16)
        elif name=='Scanlines':
            for _ in range(int(3+45*s)):
                y=int(rng.integers(h));end=min(h,y+max(1,int(h*.005*s)))
                a[y:end]=np.roll(a[y:end],int(rng.integers(-max(1,w//6),max(2,w//6+1))),axis=1)
                if rng.random()<.4:a[y:end,:,int(rng.integers(3))]=65535
        elif name=='RGB misalignment':
            d=max(1,int(w*.025*s));a[:,:,0]=np.roll(a[:,:,0],d,axis=1);a[:,:,2]=np.roll(a[:,:,2],-d,axis=0)
        elif name=='GPU tiles':
            tw=max(1,w//22);th=max(1,h//22)
            for y in range(0,h,th):
                for x in range(0,w,tw):
                    if rng.random()<.04+.4*s:
                        tile=a[y:y+th,x:x+tw];a[y:y+th,x:x+tw]=np.roll(tile,int(rng.integers(-tw,tw+1)),axis=1)
        elif name=='Bit flips':
            n=max(1,int(h*w*.03*s));ys=rng.integers(h,size=n);xs=rng.integers(w,size=n);cs=rng.integers(3,size=n)
            bits=rng.integers(8,16,size=n);a[ys,xs,cs]^=(np.uint16(1)<<bits.astype(np.uint16))
        elif name=='Memory stride':
            for _ in range(int(2+25*s)):
                y=int(rng.integers(h));end=min(h,y+max(1,int(h*.012*s)))
                a[y:end]=np.roll(a[y:end],int(rng.integers(-max(1,w//3),max(2,w//3+1))),axis=1)
        elif name=='Texture repetition':
            bw=max(1,w//12);bh=max(1,h//15)
            for _ in range(int(2+20*s)):
                sx=int(rng.integers(w-bw+1));sy=int(rng.integers(h-bh+1));dx=int(rng.integers(w-bw+1));dy=int(rng.integers(h-bh+1))
                a[dy:dy+bh,dx:dx+bw]=a[sy:sy+bh,sx:sx+bw].copy()
        elif name=='Pipeline quantization':
            bits=max(2,16-int(13*s));step=1<<(16-bits);a=(a//step*step).astype(np.uint16)
        elif name=='Shader fault':
            x0=int(rng.integers(w));y0=int(rng.integers(h));xx=np.arange(w)[None,:];yy=np.arange(h)[:,None]
            mask=((xx-x0)**2/(max(1,w*.3)**2)+(yy-y0)**2/(max(1,h*.3)**2))<1
            c=int(rng.integers(3));a[:,:,c]=np.where(mask,65535-a[:,:,c],a[:,:,c])
        elif name=='Framebuffer dropout':
            for _ in range(int(1+14*s)):
                bw=max(1,int(w*rng.uniform(.01,.15)*s));bh=max(1,int(h*rng.uniform(.01,.15)*s))
                x=int(rng.integers(w-bw+1));y=int(rng.integers(h-bh+1));a[y:y+bh,x:x+bw]=0
        elif name=='Demosaic mosaic':
            affected=rng.random(((h+1)//2,(w+1)//2))<s*.75
            red=a[:,:,0];blue=a[:,:,2];red[::2,::2]=np.where(affected,65535,red[::2,::2]);blue[::2,::2]=np.where(affected,0,blue[::2,::2])
        else:raise ValueError('Unknown effect')
    if effect=='Composite failure':
        for name in ['GPU tiles','Scanlines','RGB misalignment','Bit flips','Framebuffer dropout']:apply(name)
    else:apply(effect)
    return a
