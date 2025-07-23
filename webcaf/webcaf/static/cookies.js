const activateGtmScript = id => {
  const script = document.getElementById(id);
  const newScript = document.createElement('script');
  newScript.type = 'application/javascript';
  newScript.nonce = script.nonce;
  newScript.id = 'replaced-gtm-snippet';
  newScript.textContent = script.textContent;
  script.parentNode.replaceChild(newScript, script);
};


const banner = document.querySelector('#cookie-banner');
if (banner) {
  if (!Cookies.get('cookies_preference_set')) {
    banner.style.display = 'block';
    const cookieButtons = document.querySelectorAll('#cookie-banner .govuk-button');
    if (cookieButtons.length === 2) {
      cookieButtons[0].addEventListener('click', () => {
        Cookies.set('cookies_accepted', 'true', { secure: true, sameSite: 'strict' });
        Cookies.set('cookies_preference_set', 'true', { secure: true, sameSite: 'strict' });
        document.querySelector('#cookie-banner').style.display = 'none';
        document.querySelector('#cookie-banner-done').style.display = 'block';
        activateGtmScript('gtm-script');
      });
      cookieButtons[1].addEventListener('click', () => {
        Cookies.set('cookies_accepted', 'false', { secure: true, sameSite: 'strict' });
        Cookies.set('cookies_preference_set', 'true', { secure: true, sameSite: 'strict' });
        document.querySelector('#cookie-banner').style.display = 'none';
        document.querySelector('#cookie-banner-done').style.display = 'block';
      });
      const hideButton = document.querySelector('#cookie-banner-done .govuk-button');
      if (hideButton) {
        hideButton.addEventListener('click', () => {
          document.querySelectorAll('.cookie-banner').forEach(banner => banner.style.display='none');
        });
      }
    }
  } else {
    if (Cookies.get('cookies_accepted') === 'true') {
      activateGtmScript('gtm-script');
    }
  }
}


// Cookies page

// show controls
const cookiePageControls = document.querySelector('#cookies-analytics');
if (cookiePageControls) {
  cookiePageControls.style.display = 'block';

  const cookiesAccepted = Cookies.get('cookies_accepted') === 'true';
  document.querySelector('#use-cookies').checked = cookiesAccepted;
  document.querySelector('#no-cookies').checked = !cookiesAccepted;

  const saveButton = document.querySelector('#save-cookies');
  if (saveButton) {
    saveButton.addEventListener('click', () => {
      if (document.querySelector('#use-cookies').checked) {
        Cookies.set('cookies_preference_set', 'true', { secure: true, sameSite: 'strict' });
        Cookies.set('cookies_accepted', 'true', { secure: true, sameSite: 'strict' });
      }
      if (document.querySelector('#no-cookies').checked) {
        Cookies.set('cookies_preference_set', 'true', { secure: true, sameSite: 'strict' });
        Cookies.set('cookies_accepted', 'false', { secure: true, sameSite: 'strict' });
      }
      document.querySelector('#cookie-success-back-link').href = document.referrer;
      document.querySelector('#success-banner').style.display = 'block';
      window.scrollTo(0, 0);
    });
  }
}
