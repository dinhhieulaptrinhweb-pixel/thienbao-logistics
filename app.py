import csv, io, os, secrets, smtplib
from email.message import EmailMessage
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', secrets.token_hex(32)),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    UPLOAD_FOLDER=str(BASE_DIR / 'static' / 'uploads'),
    ALLOWED_EXTENSIONS={'png','jpg','jpeg','webp','svg'},
    ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','admin'),
    ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','ThienBao@2026'),
    SMTP_HOST=os.getenv('SMTP_HOST',''), SMTP_PORT=int(os.getenv('SMTP_PORT','587')),
    SMTP_USERNAME=os.getenv('SMTP_USERNAME',''), SMTP_PASSWORD=os.getenv('SMTP_PASSWORD',''),
    SMTP_USE_TLS=os.getenv('SMTP_USE_TLS','1') == '1', MAIL_RECEIVER=os.getenv('MAIL_RECEIVER','')
)
database_url = os.getenv('DATABASE_URL','').strip()
if not database_url or database_url == 'sqlite:///instance/thienbao.db':
    database_url = f"sqlite:///{(BASE_DIR/'instance'/'thienbao.db').as_posix()}"
app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('mysql://','mysql+pymysql://',1)
(BASE_DIR/'instance').mkdir(exist_ok=True)
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
db = SQLAlchemy(app)

class AdminUser(db.Model):
    id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(80),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Lead(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); phone=db.Column(db.String(30),nullable=False,index=True)
    email=db.Column(db.String(120)); service=db.Column(db.String(160),nullable=False); location=db.Column(db.String(255)); note=db.Column(db.Text)
    admin_note=db.Column(db.Text); status=db.Column(db.String(30),default='Mới',nullable=False,index=True); created_at=db.Column(db.DateTime,default=datetime.utcnow,index=True)
class Service(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(160),nullable=False); slug=db.Column(db.String(180),unique=True,nullable=False)
    icon=db.Column(db.String(80),default='fa-solid fa-box'); short_description=db.Column(db.String(300),nullable=False); content=db.Column(db.Text)
    image=db.Column(db.String(255)); banner_image=db.Column(db.String(255)); faq=db.Column(db.Text); seo_title=db.Column(db.String(180)); seo_description=db.Column(db.String(320))
    is_active=db.Column(db.Boolean,default=True); sort_order=db.Column(db.Integer,default=0); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Post(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(220),nullable=False); slug=db.Column(db.String(240),unique=True,nullable=False)
    excerpt=db.Column(db.String(400),nullable=False); content=db.Column(db.Text,nullable=False); image=db.Column(db.String(255)); category=db.Column(db.String(100),default='Tin tức')
    seo_title=db.Column(db.String(180)); seo_description=db.Column(db.String(320)); is_published=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow); updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class AboutContent(db.Model):
    id=db.Column(db.Integer,primary_key=True); hero_title=db.Column(db.String(220)); hero_subtitle=db.Column(db.String(400)); hero_image=db.Column(db.String(255))
    intro_title=db.Column(db.String(220)); intro_content=db.Column(db.Text); history=db.Column(db.Text); vision=db.Column(db.Text); mission=db.Column(db.Text)
    core_values=db.Column(db.Text); team_content=db.Column(db.Text); achievements=db.Column(db.Text); company_image=db.Column(db.String(255)); video_url=db.Column(db.String(500))
    seo_title=db.Column(db.String(180)); seo_description=db.Column(db.String(320)); updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class SiteSetting(db.Model):
    id=db.Column(db.Integer,primary_key=True); key=db.Column(db.String(100),unique=True,nullable=False); value=db.Column(db.Text,default='')

DEFAULT_SETTINGS={
 'company_name':'Dịch Vụ Thiên Bảo','hotline':'0866146497','email':'','address':'Hà Nội và khu vực lân cận',
 'facebook_url':'','zalo_url':'https://zalo.me/0866146497','tiktok_url':'','youtube_url':'','maps_url':'',
 'logo_text':'THIÊN BẢO','hero_title':'Bốc xếp chuyên nghiệp – Có mặt nhanh tại Hà Nội',
 'hero_subtitle':'Đội ngũ khỏe, kỷ luật, linh hoạt theo giờ, ca, ngày. Báo giá rõ ràng và cam kết tiến độ.',
 'hero_image':'','footer_text':'Bốc xếp, vận chuyển và cung ứng nhân công chuyên nghiệp.','copyright':'Dịch Vụ Thiên Bảo',
 'ga_id':'','gtm_id':'','facebook_pixel':'','site_url':'http://127.0.0.1:5000'
}

def slugify(text):
    import re, unicodedata
    text=unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[^a-zA-Z0-9]+','-',text).strip('-').lower() or secrets.token_hex(4)
def unique_slug(model,title,current_id=None):
    base=slugify(title); slug=base; n=2
    while True:
        q=model.query.filter_by(slug=slug)
        if current_id: q=q.filter(model.id!=current_id)
        if not q.first(): return slug
        slug=f'{base}-{n}'; n+=1
def allowed_file(name): return '.' in name and name.rsplit('.',1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
def save_upload(fs):
    if not fs or not fs.filename: return None
    if not allowed_file(fs.filename): raise ValueError('Chỉ chấp nhận PNG, JPG, JPEG, WEBP hoặc SVG.')
    ext=secure_filename(fs.filename).rsplit('.',1)[1].lower(); name=f'{datetime.utcnow():%Y%m%d%H%M%S}-{secrets.token_hex(5)}.{ext}'
    fs.save(Path(app.config['UPLOAD_FOLDER'])/name); return name
def setting(key,default=''):
    row=SiteSetting.query.filter_by(key=key).first(); return row.value if row else DEFAULT_SETTINGS.get(key,default)
def set_setting(key,value):
    row=SiteSetting.query.filter_by(key=key).first()
    if row: row.value=value
    else: db.session.add(SiteSetting(key=key,value=value))
def csrf_token():
    if '_csrf' not in session: session['_csrf']=secrets.token_urlsafe(24)
    return session['_csrf']
def check_csrf():
    if request.method=='POST' and request.form.get('_csrf') != session.get('_csrf'): abort(400)
def admin_required(fn):
    @wraps(fn)
    def wrap(*a,**k):
        if not session.get('admin_id'): return redirect(url_for('admin_login',next=request.path))
        return fn(*a,**k)
    return wrap

@app.context_processor
def globals_ctx():
    
    site={k:setting(k,v) for k,v in DEFAULT_SETTINGS.items()}
    site.update({'logo_image':setting('logo_image'),'favicon':setting('favicon'),'hero_image':setting('hero_image')})
    return {'site':site,'current_year':datetime.now().year,'csrf_token':csrf_token}
@app.before_request
def csrf_guard():
    if request.method=='POST': check_csrf()

@app.get('/')
def index():
    services=Service.query.filter_by(is_active=True).order_by(Service.sort_order,Service.id).all(); posts=Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).limit(3).all()
    about=AboutContent.query.first(); return render_template('index.html',services=services,posts=posts,about=about)
@app.get('/gioi-thieu')
def about(): return render_template('about.html',about=AboutContent.query.first())
@app.post('/bao-gia')
def submit_quote():
    name=request.form.get('name','').strip(); phone=request.form.get('phone','').strip(); service_name=request.form.get('service','').strip()
    if len(name)<2 or len(''.join(x for x in phone if x.isdigit()))<9 or not service_name:
        flash('Vui lòng nhập đầy đủ thông tin hợp lệ.','error'); return redirect(url_for('index')+'#bao-gia')
    lead=Lead(name=name,phone=phone,email=request.form.get('email','').strip(),service=service_name,location=request.form.get('location','').strip(),note=request.form.get('note','').strip())
    db.session.add(lead); db.session.commit(); flash('Đã gửi yêu cầu. Thiên Bảo sẽ liên hệ sớm.','success'); return redirect(url_for('index')+'#bao-gia')
@app.get('/dich-vu/<slug>')
def service_detail(slug): return render_template('service_detail.html',service=Service.query.filter_by(slug=slug,is_active=True).first_or_404())
@app.get('/tin-tuc')
def posts_list():
    category=request.args.get('category',''); q=Post.query.filter_by(is_published=True)
    if category: q=q.filter_by(category=category)
    return render_template('posts.html',posts=q.order_by(Post.created_at.desc()).all(),categories=[x[0] for x in db.session.query(Post.category).distinct().all()])
@app.get('/tin-tuc/<slug>')
def post_detail(slug): return render_template('post_detail.html',post=Post.query.filter_by(slug=slug,is_published=True).first_or_404())
@app.get('/robots.txt')
def robots(): return Response(f"User-agent: *\nAllow: /\nSitemap: {url_for('sitemap',_external=True)}",mimetype='text/plain')
@app.get('/sitemap.xml')
def sitemap():
    pages=[url_for('index',_external=True),url_for('about',_external=True),url_for('posts_list',_external=True)]
    pages += [url_for('service_detail',slug=x.slug,_external=True) for x in Service.query.filter_by(is_active=True)]
    pages += [url_for('post_detail',slug=x.slug,_external=True) for x in Post.query.filter_by(is_published=True)]
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{p}</loc></url>' for p in pages)+'</urlset>',mimetype='application/xml')
@app.get('/health')
def health(): return {'status':'ok','database':'connected'}

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        user=AdminUser.query.filter_by(username=request.form.get('username','').strip()).first()
        if user and check_password_hash(user.password_hash,request.form.get('password','')):
            session.clear(); session['admin_id']=user.id; session['admin_username']=user.username; return redirect(url_for('admin_dashboard'))
        flash('Sai tài khoản hoặc mật khẩu.','error')
    return render_template('admin/login.html')
@app.get('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('admin_login'))
@app.get('/admin')
@admin_required
def admin_dashboard():
    recent=Lead.query.order_by(Lead.created_at.desc()).limit(8).all(); last7=db.session.query(func.date(Lead.created_at),func.count(Lead.id)).group_by(func.date(Lead.created_at)).order_by(func.date(Lead.created_at).desc()).limit(7).all()
    return render_template('admin/dashboard.html',total_leads=Lead.query.count(),new_leads=Lead.query.filter_by(status='Mới').count(),total_services=Service.query.count(),total_posts=Post.query.count(),recent_leads=recent,chart_data=list(reversed(last7)))
@app.get('/admin/leads')
@admin_required
def admin_leads():
    q=Lead.query; keyword=request.args.get('q','').strip(); status=request.args.get('status','').strip()
    if keyword: q=q.filter(or_(Lead.name.ilike(f'%{keyword}%'),Lead.phone.ilike(f'%{keyword}%'),Lead.service.ilike(f'%{keyword}%')))
    if status: q=q.filter_by(status=status)
    return render_template('admin/leads.html',leads=q.order_by(Lead.created_at.desc()).all(),keyword=keyword,selected_status=status)
@app.post('/admin/leads/<int:lead_id>/update')
@admin_required
def admin_lead_update(lead_id):
    lead=Lead.query.get_or_404(lead_id); lead.status=request.form.get('status','Mới'); lead.admin_note=request.form.get('admin_note','').strip(); db.session.commit(); flash('Đã cập nhật khách hàng.','success'); return redirect(url_for('admin_leads'))
@app.post('/admin/leads/<int:lead_id>/delete')
@admin_required
def admin_lead_delete(lead_id):
    db.session.delete(Lead.query.get_or_404(lead_id)); db.session.commit(); flash('Đã xóa yêu cầu.','success'); return redirect(url_for('admin_leads'))
@app.get('/admin/leads/export.csv')
@admin_required
def admin_leads_export():
    out=io.StringIO(); out.write('\ufeff'); w=csv.writer(out); w.writerow(['ID','Họ tên','Điện thoại','Email','Dịch vụ','Địa điểm','Nội dung','Ghi chú','Trạng thái','Ngày'])
    for x in Lead.query.order_by(Lead.created_at.desc()): w.writerow([x.id,x.name,x.phone,x.email,x.service,x.location,x.note,x.admin_note,x.status,x.created_at.strftime('%d/%m/%Y %H:%M')])
    return Response(out.getvalue(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=khach-hang-thien-bao.csv'})

def service_from_form(obj=None):
    obj=obj or Service(); title=request.form['title'].strip(); obj.title=title; obj.slug=unique_slug(Service,title,obj.id); obj.icon=request.form.get('icon','fa-solid fa-box').strip() or 'fa-solid fa-box'
    obj.short_description=request.form['short_description'].strip(); obj.content=request.form.get('content','').strip(); obj.faq=request.form.get('faq','').strip(); obj.seo_title=request.form.get('seo_title','').strip(); obj.seo_description=request.form.get('seo_description','').strip(); obj.sort_order=int(request.form.get('sort_order') or 0); obj.is_active=bool(request.form.get('is_active'))
    image=save_upload(request.files.get('image')); banner=save_upload(request.files.get('banner_image'))
    if image: obj.image=image
    if banner: obj.banner_image=banner
    return obj
@app.route('/admin/services',methods=['GET','POST'])
@admin_required
def admin_services():
    if request.method=='POST':
        try: db.session.add(service_from_form()); db.session.commit(); flash('Đã thêm dịch vụ.','success')
        except Exception as e: db.session.rollback(); flash(f'Không thể thêm: {e}','error')
        return redirect(url_for('admin_services'))
    return render_template('admin/services.html',services=Service.query.order_by(Service.sort_order).all())
@app.route('/admin/services/<int:id>/edit',methods=['GET','POST'])
@admin_required
def admin_service_edit(id):
    obj=Service.query.get_or_404(id)
    if request.method=='POST':
        try: service_from_form(obj); db.session.commit(); flash('Đã cập nhật dịch vụ.','success'); return redirect(url_for('admin_services'))
        except Exception as e: db.session.rollback(); flash(str(e),'error')
    return render_template('admin/service_edit.html',service=obj)
@app.post('/admin/services/<int:id>/delete')
@admin_required
def admin_service_delete(id): db.session.delete(Service.query.get_or_404(id)); db.session.commit(); return redirect(url_for('admin_services'))

def post_from_form(obj=None):
    obj=obj or Post(); title=request.form['title'].strip(); obj.title=title; obj.slug=unique_slug(Post,title,obj.id); obj.excerpt=request.form['excerpt'].strip(); obj.content=request.form['content'].strip(); obj.category=request.form.get('category','Tin tức').strip() or 'Tin tức'; obj.seo_title=request.form.get('seo_title','').strip(); obj.seo_description=request.form.get('seo_description','').strip(); obj.is_published=bool(request.form.get('is_published')); image=save_upload(request.files.get('image')); obj.image=image or obj.image; return obj
@app.route('/admin/posts',methods=['GET','POST'])
@admin_required
def admin_posts():
    if request.method=='POST':
        try: db.session.add(post_from_form()); db.session.commit(); flash('Đã thêm bài viết.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'error')
        return redirect(url_for('admin_posts'))
    return render_template('admin/posts.html',posts=Post.query.order_by(Post.created_at.desc()).all())
@app.route('/admin/posts/<int:id>/edit',methods=['GET','POST'])
@admin_required
def admin_post_edit(id):
    obj=Post.query.get_or_404(id)
    if request.method=='POST':
        try: post_from_form(obj); db.session.commit(); flash('Đã cập nhật bài viết.','success'); return redirect(url_for('admin_posts'))
        except Exception as e: db.session.rollback(); flash(str(e),'error')
    return render_template('admin/post_edit.html',post=obj)
@app.post('/admin/posts/<int:id>/delete')
@admin_required
def admin_post_delete(id): db.session.delete(Post.query.get_or_404(id)); db.session.commit(); return redirect(url_for('admin_posts'))

@app.route('/admin/about',methods=['GET','POST'])
@admin_required
def admin_about():
    obj=AboutContent.query.first() or AboutContent()
    if not obj.id: db.session.add(obj)
    if request.method=='POST':
        for key in ['hero_title','hero_subtitle','intro_title','intro_content','history','vision','mission','core_values','team_content','achievements','video_url','seo_title','seo_description']: setattr(obj,key,request.form.get(key,'').strip())
        hero=save_upload(request.files.get('hero_image')); company=save_upload(request.files.get('company_image'))
        if hero: obj.hero_image=hero
        if company: obj.company_image=company
        db.session.commit(); flash('Đã cập nhật trang Giới thiệu.','success'); return redirect(url_for('admin_about'))
    return render_template('admin/about.html',about=obj)
@app.route('/admin/settings',methods=['GET','POST'])
@admin_required
def admin_settings():
    if request.method=='POST':
        for key in DEFAULT_SETTINGS: set_setting(key,request.form.get(key,'').strip())
        logo=save_upload(request.files.get('logo_image')); favicon=save_upload(request.files.get('favicon'))
        if logo: set_setting('logo_image',logo)
        if favicon: set_setting('favicon',favicon)
        db.session.commit(); flash('Đã lưu cấu hình website.','success'); return redirect(url_for('admin_settings'))
    values={k:setting(k,v) for k,v in DEFAULT_SETTINGS.items()}; values['logo_image']=setting('logo_image'); values['favicon']=setting('favicon')
    return render_template('admin/settings.html',values=values)
@app.route('/admin/change-password',methods=['GET','POST'])
@admin_required
def admin_change_password():
    user=AdminUser.query.get(session['admin_id'])
    if request.method=='POST':
        if not check_password_hash(user.password_hash,request.form.get('current_password','')): flash('Mật khẩu hiện tại không đúng.','error')
        elif len(request.form.get('new_password',''))<8: flash('Mật khẩu mới cần ít nhất 8 ký tự.','error')
        elif request.form.get('new_password')!=request.form.get('confirm_password'): flash('Xác nhận mật khẩu không khớp.','error')
        else: user.password_hash=generate_password_hash(request.form['new_password']); db.session.commit(); flash('Đổi mật khẩu thành công.','success'); return redirect(url_for('admin_dashboard'))
    return render_template('admin/change_password.html')

@app.errorhandler(413)
def too_large(_): flash('Ảnh vượt quá 8 MB.','error'); return redirect(request.referrer or url_for('admin_dashboard'))

def seed_data():
    for k,v in DEFAULT_SETTINGS.items():
        if not SiteSetting.query.filter_by(key=k).first(): db.session.add(SiteSetting(key=k,value=v))
    if not AdminUser.query.first(): db.session.add(AdminUser(username=app.config['ADMIN_USERNAME'],password_hash=generate_password_hash(app.config['ADMIN_PASSWORD'])))
    if not AboutContent.query.first(): db.session.add(AboutContent(hero_title='Về Thiên Bảo',hero_subtitle='Đơn vị bốc xếp, vận chuyển và cung ứng nhân công chuyên nghiệp tại Hà Nội.',intro_title='Đối tác nhân lực đáng tin cậy',intro_content='Thiên Bảo cung cấp giải pháp nhân lực linh hoạt, có người điều phối và quy trình rõ ràng cho kho bãi, nhà xưởng, văn phòng.',history='Từ những đội nhân công nhỏ, Thiên Bảo từng bước xây dựng hệ thống điều phối chuyên nghiệp nhằm phục vụ doanh nghiệp nhanh và ổn định hơn.',vision='Trở thành đơn vị cung ứng nhân lực và logistics được khách hàng tin tưởng tại Hà Nội và miền Bắc.',mission='Giúp doanh nghiệp chủ động nhân lực, giảm chi phí vận hành và bảo đảm tiến độ.',core_values='Trách nhiệm\nKỷ luật\nAn toàn\nTốc độ\nMinh bạch',team_content='Đội ngũ khỏe, có kinh nghiệm thực tế và được phân công theo đúng tính chất công việc.',achievements='100+ nhân công linh hoạt\nPhục vụ 24/7\nNhiều nhóm dịch vụ chuyên biệt'))
    if Service.query.count()==0:
        data=[('Bốc xếp hàng hóa','fa-solid fa-box','Bốc dỡ xe tải, container, pallet và hàng đóng kiện.',1),('Bốc xếp kho bãi','fa-solid fa-warehouse','Sắp xếp, phân loại, nhập xuất và di chuyển hàng hóa.',2),('Chuyển nhà xưởng','fa-solid fa-truck','Di dời máy móc, thiết bị và vật tư an toàn.',3),('Chuyển văn phòng','fa-solid fa-building','Đóng gói, vận chuyển và bố trí tài sản văn phòng.',4),('Cho thuê nhân công','fa-solid fa-users','Cung ứng lao động theo giờ, ca, ngày hoặc dài hạn.',5),('Dọn kho, mặt bằng','fa-solid fa-broom','Thu gom, sắp xếp và giải phóng mặt bằng.',6)]
        for t,i,d,o in data: db.session.add(Service(title=t,slug=unique_slug(Service,t),icon=i,short_description=d,content=d,sort_order=o))
    if Post.query.count()==0:
        t='Kinh nghiệm thuê dịch vụ bốc xếp an toàn và tiết kiệm'; db.session.add(Post(title=t,slug=unique_slug(Post,t),excerpt='Các tiêu chí quan trọng khi lựa chọn đội bốc xếp.',content='<p>Hãy thống nhất rõ khối lượng công việc, thời gian, số lượng nhân công, trách nhiệm đối với hàng hóa và mức giá trước khi triển khai.</p>'))
    db.session.commit()
with app.app_context(): db.create_all(); seed_data()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG','0')=='1')
