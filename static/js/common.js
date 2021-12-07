darkbtn = document.getElementById('dark-mode');
darkbtn.addEventListener('click', function() {
    if (getDarkCookie() == 'true') {
        setDarkCookie(false);
        document.getElementById('theme-css').href = '/static/css/' + 'light.css' + cssversion;
    } else {
        setDarkCookie(true);
        document.getElementById('theme-css').href = '/static/css/' + 'dark.css' + cssversion;
    }
});
