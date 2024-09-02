from webservices import app
port = "7030"
debug = False

if __name__ == "__main__":
    app.run(port=port, debug=debug, use_reloader=False)
    