$(function () {

  function shiftWindow() {
    var navbarHeight = $('.navbar').height();
    if (navbarHeight) {
      scrollBy(0, -navbarHeight);
    }
  }
  if (window.location.hash) {
    shiftWindow();
  }
  window.addEventListener("hashchange", shiftWindow);

});
