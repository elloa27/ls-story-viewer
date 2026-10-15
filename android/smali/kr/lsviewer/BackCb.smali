.class public Lkr/lsviewer/BackCb;
.super Ljava/lang/Object;
.implements Landroid/webkit/ValueCallback;

.field private a:Lkr/lsviewer/MainActivity;

.method public constructor <init>(Lkr/lsviewer/MainActivity;)V
    .registers 2
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lkr/lsviewer/BackCb;->a:Lkr/lsviewer/MainActivity;
    return-void
.end method

.method public onReceiveValue(Ljava/lang/Object;)V
    .registers 4
    const-string v0, "1"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-nez v1, :handled
    iget-object v0, p0, Lkr/lsviewer/BackCb;->a:Lkr/lsviewer/MainActivity;
    invoke-virtual {v0}, Lkr/lsviewer/MainActivity;->reallyBack()V
    :handled
    return-void
.end method
