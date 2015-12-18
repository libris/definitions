$(function () {

function setActive(item) {
  console.log("going to " + item);
  $('body').scrollTop($(item).offset().top - 75);
};

$('body').ready(function() {
  $('.main-nav a').click(function(e){
    e.preventDefault();
    setActive($(this).attr('href'));
  });
});

});
