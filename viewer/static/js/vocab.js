window.onload = function () {

  function accept(id) { return id.indexOf(':') == -1 }

  var nodes = Array.prototype.map.call(document.querySelectorAll(".rdf-class"), function (el) {
    return accept(el.id)? {
      name: el.id,
      children: Array.prototype.map.call(el.querySelectorAll(".rdf-subclasses a"), function (el) {
        var ref = el.getAttribute('href')
        return ref[0] == '#' && accept(ref)? ref.substring(1) : null
      }).filter(function (it) { return it })
    } : null
  }).filter(function (it) { return it })

  var graphView = null
  var loaded = false

  var classNav = document.querySelector('nav > section > b')
  classNav.addEventListener('click', function () {
    document.body.classList.toggle('graph')
    if (loaded)
      return
    graphView = new GraphView(0.8)
    graphView.viewData({nodes: nodes}, function (d) {
      if (d.name) {
        document.location = '#' + d.name
      }
    })
    loaded = true
  })
  var toggle = document.createElement("div")
  toggle.classList.add('toggle')
  toggle.innerHTML = "&otimes;"
  document.body.appendChild(toggle)
  toggle.addEventListener('click', function () {
    document.body.classList.toggle('graph')
  })

}
