const menu=document.querySelector('.menu');if(menu)menu.addEventListener('click',()=>document.querySelector('.links').classList.toggle('show'));
const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('visible')}),{threshold:.1});document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
setTimeout(()=>document.querySelectorAll('.flash').forEach(x=>x.remove()),5000);
