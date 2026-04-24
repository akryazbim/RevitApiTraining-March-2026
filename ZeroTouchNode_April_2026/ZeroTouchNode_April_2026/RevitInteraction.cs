using Revit.Elements;
using Autodesk.Revit.DB;
using RevitServices.Persistence;
using RevitServices.Transactions;

//import Autodesk.Revit.DB

namespace ZeroTouchNode_April_2025;

public class RevitInteraction
{
    //def GetElementName(Element):
    //    eleName = Element.Name
    //    return eleName

    public static string GetElementName(Revit.Elements.Element Element)
    {
        var eleName = Element.Name;
        return eleName;
    }

    public static int GetWallCount()
    {
        var doc = DocumentManager.Instance.CurrentDBDocument;
        var walls = new FilteredElementCollector(doc).OfClass(typeof(Autodesk.Revit.DB.Wall)).ToElements();

        //var walls2 = new FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements();

        return walls.Count;
    }
    //  public static Wall Create(
    //    Document document,
    //    Curve curve,
    //    ElementId levelId,
    //    bool structural
    //)


    public static Revit.Elements.Element CreateWall(Revit.Elements.Level Level)
    {
        var doc = DocumentManager.Instance.CurrentDBDocument;
        var sp = new XYZ(0, 0, 0);
        var ep = new XYZ(100, 0, 0);

        var curve = Line.CreateBound(sp, ep);

        var levelId = new ElementId(Level.Id);

        TransactionManager.Instance.EnsureInTransaction(doc);


        var newWall = Autodesk.Revit.DB.Wall.Create(doc, curve, levelId, true);    


        TransactionManager.Instance.TransactionTaskDone();

        return newWall.ToDSType(true);
    }
}
