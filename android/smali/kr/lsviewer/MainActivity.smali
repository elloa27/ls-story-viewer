.class public Lkr/lsviewer/MainActivity;
.super Landroid/app/Activity;

.field public web:Landroid/webkit/WebView;

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .registers 7
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    invoke-virtual {p0}, Lkr/lsviewer/MainActivity;->getWindow()Landroid/view/Window;
    move-result-object v3
    const/high16 v4, -0x1000000
    invoke-virtual {v3, v4}, Landroid/view/Window;->setStatusBarColor(I)V
    invoke-virtual {v3, v4}, Landroid/view/Window;->setNavigationBarColor(I)V
    new-instance v0, Landroid/webkit/WebView;
    invoke-direct {v0, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V
    iput-object v0, p0, Lkr/lsviewer/MainActivity;->web:Landroid/webkit/WebView;
    invoke-virtual {v0, v4}, Landroid/webkit/WebView;->setBackgroundColor(I)V
    invoke-virtual {v0}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;
    move-result-object v1
    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setAllowFileAccess(Z)V
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setAllowFileAccessFromFileURLs(Z)V
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setAllowUniversalAccessFromFileURLs(Z)V
    const/4 v2, 0x0
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setMediaPlaybackRequiresUserGesture(Z)V
    const/16 v2, 0x64
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setTextZoom(I)V
    invoke-virtual {p0, v0}, Lkr/lsviewer/MainActivity;->setContentView(Landroid/view/View;)V
    const/4 v2, 0x0
    invoke-virtual {p0, v2}, Lkr/lsviewer/MainActivity;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    if-eqz p1, :fresh
    invoke-virtual {v0, p1}, Landroid/webkit/WebView;->restoreState(Landroid/os/Bundle;)Landroid/webkit/WebBackForwardList;
    move-result-object v1
    if-nez v1, :done
    :fresh
    const-string v1, "file:///android_asset/index.html"
    invoke-virtual {v0, v1}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V
    :done
    return-void
.end method

.method protected onSaveInstanceState(Landroid/os/Bundle;)V
    .registers 3
    invoke-super {p0, p1}, Landroid/app/Activity;->onSaveInstanceState(Landroid/os/Bundle;)V
    iget-object v0, p0, Lkr/lsviewer/MainActivity;->web:Landroid/webkit/WebView;
    invoke-virtual {v0, p1}, Landroid/webkit/WebView;->saveState(Landroid/os/Bundle;)Landroid/webkit/WebBackForwardList;
    return-void
.end method

.method public onBackPressed()V
    .registers 4
    iget-object v0, p0, Lkr/lsviewer/MainActivity;->web:Landroid/webkit/WebView;
    const-string v1, "(window.lsBack&&window.lsBack())?1:0"
    new-instance v2, Lkr/lsviewer/BackCb;
    invoke-direct {v2, p0}, Lkr/lsviewer/BackCb;-><init>(Lkr/lsviewer/MainActivity;)V
    invoke-virtual {v0, v1, v2}, Landroid/webkit/WebView;->evaluateJavascript(Ljava/lang/String;Landroid/webkit/ValueCallback;)V
    return-void
.end method

.method public reallyBack()V
    .registers 1
    invoke-super {p0}, Landroid/app/Activity;->onBackPressed()V
    return-void
.end method
